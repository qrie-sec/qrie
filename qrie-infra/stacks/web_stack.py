import aws_cdk as cdk
from aws_cdk import (
    Stack, Duration,
    aws_s3 as s3,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_certificatemanager as acm,
    aws_route53 as route53,
)

class WebStack(Stack):
    def __init__(self, scope: cdk.App, construct_id: str, ui_domain: str | None = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        site_bucket = s3.Bucket(
            self, "QrieUiBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # OAC for private S3 origin
        oac = cf.CfnOriginAccessControl(
            self,
            "UiOAC",
            origin_access_control_config=cf.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                # CloudFront OAC is a global resource (per account), and its name must be unique.
                # Appending the account ID and stack name prevents collisions across regions/stacks.
                name=f"QrieUiOAC-{cdk.Aws.ACCOUNT_ID}-{cdk.Aws.REGION}-{self.stack_name}",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",
            ),
        )

        # Configure custom domain if provided
        domain_names = None
        certificate = None
        
        # Create CloudFront function for URL rewriting (for Next.js static export)
        # This is to allow users to provide URLs like 'https://domain.com/findings' which this function modifies to 'https://domain.com/findings.html' to return the correct page.
        url_rewrite_function = cf.Function(
            self, "UrlRewriteFunction",
            code=cf.FunctionCode.from_inline("""
function handler(event) {
    var request = event.request;
    var uri = request.uri;
    
    // If the URI doesn't have an extension and isn't root, append .html
    if (!uri.includes('.') && uri !== '/') {
        request.uri = uri + '.html';
    }
    
    return request;
}
            """),
            comment="Rewrite URLs to append .html for Next.js static export"
        )

        if ui_domain:
            # Create SSL certificate for the custom domain
            certificate = acm.Certificate(
                self, "UiCertificate",
                domain_name=ui_domain,
                validation=acm.CertificateValidation.from_dns(),
                # Certificate must be in us-east-1 for CloudFront
                region="us-east-1"
            )
            domain_names = [ui_domain]

        distro = cf.Distribution(
            self, "QrieUiCdn",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin(site_bucket),
                origin_request_policy=cf.OriginRequestPolicy.CORS_S3_ORIGIN,
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                function_associations=[
                    cf.FunctionAssociation(
                        function=url_rewrite_function,
                        event_type=cf.FunctionEventType.VIEWER_REQUEST
                    )
                ],
            ),
            domain_names=domain_names,
            certificate=certificate,
            default_root_object="index.html",
            error_responses=[
                # For missing files, serve 404.html
                cf.ErrorResponse(
                    http_status=404,
                    response_http_status=404,
                    response_page_path="/404.html",
                    ttl=Duration.seconds(0),
                ),
                cf.ErrorResponse(
                    http_status=403,
                    response_http_status=404,
                    response_page_path="/404.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # Attach OAC to the S3 origin (CloudFront L1 override)
        cfn_dist = distro.node.default_child
        cfn_dist.add_property_override(
            "DistributionConfig.Origins.0.OriginAccessControlId",
            oac.attr_id,
        )

        # Bucket policy to allow CloudFront (via OAC) to read objects
        site_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontServicePrincipalReadOnly",
                actions=["s3:GetObject"],
                resources=[site_bucket.arn_for_objects("*")],
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{cdk.Aws.ACCOUNT_ID}:distribution/{distro.distribution_id}"
                    }
                },
            )
        )

        cdk.CfnOutput(self, "UiBucketName", value=site_bucket.bucket_name)
        cdk.CfnOutput(self, "UiDistributionDomain", value=distro.distribution_domain_name)
        cdk.CfnOutput(self, "UiDistributionId", value=distro.distribution_id)
        
        # Output the custom domain if configured, otherwise the CloudFront domain
        ui_url = ui_domain if ui_domain else distro.distribution_domain_name
        cdk.CfnOutput(self, "UiUrl", value=f"https://{ui_url}")
        
        if ui_domain:
            cdk.CfnOutput(self, "UiCustomDomain", value=ui_domain)