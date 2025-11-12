// app/api/lead/route.ts
import { NextResponse } from "next/server";
import { DynamoDBClient, PutItemCommand, AttributeValue } from "@aws-sdk/client-dynamodb";

export const runtime = "nodejs"; // ensure Node runtime (AWS SDK v3 needs it)

const client = new DynamoDBClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID as string,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY as string,
  },
});

const TABLE = process.env.SIGNUPS_TABLE as string;

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as unknown;
    const { email, name, organization, marketing } = (body ?? {}) as {
      email?: unknown;
      name?: unknown;
      organization?: unknown;
      marketing?: unknown;
    };

    if (!email || typeof email !== "string") {
      return NextResponse.json({ error: "email required" }, { status: 400 });
    }
    if (!name || typeof name !== "string" || name.trim() === "") {
      return NextResponse.json({ error: "name required" }, { status: 400 });
    }

    // Build DynamoDB item
    const item: Record<string, AttributeValue> = {
      pk: { S: `email#${email.toLowerCase()}` },
      sk: { S: new Date().toISOString() },
      email: { S: email.toLowerCase() },
      name: { S: (name ?? "").toString() },
      src: { S: "landing" },
    };

    const orgStr = organization != null ? organization.toString().trim() : "";
    if (orgStr) item.organization = { S: orgStr };

    // Accept marketing as a plain object of string-like values and store as a Map
    if (marketing && typeof marketing === "object" && !Array.isArray(marketing)) {
      const entries = Object.entries(marketing as Record<string, unknown>)
        .filter(([k, v]) => typeof k === "string" && v != null && String(v).trim() !== "");
      if (entries.length) {
        item.mkt = {
          M: Object.fromEntries(
            entries.map(([k, v]) => [k, { S: String(v) } as AttributeValue])
          ),
        };
      }
    }

    await client.send(
      new PutItemCommand({
        TableName: TABLE,
        Item: item,
        ConditionExpression: "attribute_not_exists(pk)",
      })
    );

    return NextResponse.json({ ok: true });
  } catch (err: unknown) {
    const maybeName = (err as { name?: unknown })?.name;
    if (typeof maybeName === "string" && maybeName.includes("ConditionalCheckFailed")) {
      return NextResponse.json({ ok: true });
    }
    console.error(err);
    return NextResponse.json({ error: "server_error" }, { status: 500 });
  }
}
