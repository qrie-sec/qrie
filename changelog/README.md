# Qrie Changelog

This directory contains daily changelog entries, documentation, roadmaps, and completed work documenting all changes, improvements, and fixes to the Qrie platform.

## Directory Structure

```
changelog/
├── YYYY-MM/              # Monthly folders for daily changelogs
│   └── YYYY-MM-DD-<desc>.md
├── documentation/        # Technical documentation and architecture
├── roadmap/             # Future plans, proposals, and roadmaps
├── completed_work/      # Archived completed implementations
├── CHANGELOG.md         # Legacy consolidated changelog (deprecated)
└── README.md           # This file
```

## File Organization

### Daily Changelogs (`YYYY-MM/YYYY-MM-DD-<desc>.md`)
- **Location**: `changelog/YYYY-MM/` folders (e.g., `changelog/2025-11/`)
- **Format**: `YYYY-MM-DD-<description>.md` (e.g., `2025-11-06-api-enhancements.md`)
- **Purpose**: Concise, user-facing summaries of what changed each day
- **Sections**:
  - 🚀 **New Features**: Major new functionality
  - 🏗️ **Infrastructure Changes**: AWS infrastructure and deployment changes
  - 🔧 **Developer Experience**: Tooling and development workflow improvements
  - 🐛 **Bug Fixes**: Issues resolved
  - 📚 **Documentation Updates**: Documentation improvements
  - 🔄 **Maintenance**: Code cleanup and refactoring
  - ⚡ **Performance**: Performance improvements

### Documentation (`documentation/`)
- **Purpose**: Technical documentation, architecture diagrams, and system design
- **Examples**:
  - `qrie-architecture.md` - Overall system architecture
  - `workflows-inventory-events-scans.md` - Workflow documentation
  - API specifications, data models, etc.
- **When to use**: For reference documentation that doesn't change frequently

### Roadmap (`roadmap/`)
- **Purpose**: Future plans, proposals, and feature roadmaps
- **Examples**:
  - `2025-10-15-policies-roadmap-DOC.md` - Policy implementation roadmap
  - `2025-10-00-generic-query-filtering.md` - Proposed feature
- **When to use**: For planning documents, proposals, and future work
- **Naming**: `YYYY-MM-DD-<description>.md` or `YYYY-MM-00-<topic>.md` for month-level plans

### Completed Work (`completed_work/`)
- **Purpose**: Archive of completed implementations and detailed technical write-ups
- **Examples**:
  - `10-30-phase3-complete.md` - Completed phase documentation
  - `10-31-inventory-analysis-complete.md` - Completed analysis
- **When to use**: Move detailed implementation docs here after completion
- **Includes**: Test results, coverage reports, implementation notes

## Recent Changes

- [2025-11-05](./2025-11/2025-11-05-service-registry-refactor.md) - Service registry refactor
- [2025-11-04](./2025-11/2025-11-04-real-time-event-processing.md) - Real-time event processing
- [2025-10-31](./2025-10/2025-10-31.md) - Data purge enhancements, inventory filtering
- [2025-10-30](./2025-10/2025-10-30-inventory-caching.md) - Inventory summary caching
- [2025-10-16](./2025-10/2025-10-16.md) - Policy launch/update APIs

## Usage Guidelines

### When making changes:

1. **Daily Work**: Add entries to today's changelog in `YYYY-MM/YYYY-MM-DD-<desc>.md`
   - If no file exists for today, create one using the template below
   - Use descriptive filenames: `2025-11-06-api-enhancements.md` not just `2025-11-06.md`
   - Group related changes under appropriate emoji sections

2. **Documentation**: Add/update files in `documentation/`
   - Architecture diagrams and system design
   - Workflow documentation
   - API specifications

3. **Proposals**: Add new proposals to `roadmap/`
   - Future feature plans
   - Architecture proposals
   - Roadmaps and planning documents

4. **Completed Work**: Move detailed implementation docs to `completed_work/`
   - After a feature is complete and merged
   - Include test results and coverage reports
   - Keep as reference for future work

## Daily Changelog Template

Create new daily changelogs in `changelog/YYYY-MM/YYYY-MM-DD-<description>.md`:

```markdown
# Changelog - YYYY-MM-DD - <Brief Description>

**Date:** Month DD, YYYY  
**Status:** Active/Complete

## 🚀 New Features
- Description of new feature with relevant details
- Include code examples or commands if helpful

## 🏗️ Infrastructure Changes
- Infrastructure change description
- CDK stack changes, AWS resource modifications

## 🔧 Developer Experience
- Developer tooling improvement
- Build process, testing, debugging enhancements

## 🐛 Bug Fixes
- **Issue**: Description of the bug
- **Root Cause**: Why it happened
- **Solution**: How it was fixed
- **Files Modified**: List of changed files

## 📚 Documentation Updates
- Documentation changes
- README updates, API docs, etc.

## 🔄 Maintenance
- Code cleanup or refactoring
- Dependency updates

## ⚡ Performance
- Performance improvement with metrics
- Before/after comparisons

---

## Notes
- Additional context or follow-up items
- Links to related issues or PRs
```

## Criticism Welcome

This structure aims to:
- **Organize by time**: Monthly folders prevent root clutter
- **Separate concerns**: Documentation, roadmap, and completed work are distinct
- **Easy navigation**: Clear folder names and consistent naming conventions
- **Scalability**: Structure works as project grows

Feedback and improvements are welcome! If you find this structure doesn't work well, please propose changes.
