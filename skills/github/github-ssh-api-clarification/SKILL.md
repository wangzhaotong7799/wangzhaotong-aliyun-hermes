---
name: github-ssh-api-clarification
description: Clarifies the difference between GitHub SSH authentication (for Git operations) and API authentication (for repository management), based on practical troubleshooting experience.
tags: [GitHub, SSH, API, authentication, troubleshooting]
category: github
---

# GitHub SSH vs API Authentication Clarification

This skill clarifies the crucial distinction between GitHub SSH authentication (for Git operations) and API authentication (for repository management), based on practical troubleshooting experience.

## The Core Distinction

### SSH Authentication
- **Purpose**: Git operations only (clone, push, pull, fetch)
- **Test command**: `ssh -T git@github.com`
- **Expected response**: "Hi <username>! You've successfully authenticated..."
- **Limitation**: Does NOT grant access to GitHub REST API

### API Authentication
- **Purpose**: GitHub REST API operations (create repo, manage issues, webhooks, etc.)
- **Methods**: Personal access tokens, GitHub CLI (`gh`), OAuth apps
- **Required for**: Creating repositories, managing issues via API, webhook management

## Common Confusion Scenario

**Symptom**: SSH authentication succeeds but repository operations fail
```
$ ssh -T git@github.com
Hi username! You've successfully authenticated...

$ git clone git@github.com:owner/repo.git
ERROR: Repository not found.
```

**Root Causes**:
1. Repository doesn't exist yet (SSH can't create repositories)
2. Repository name is incorrect (GitHub is case-sensitive)
3. Repository is private and SSH key doesn't have access
4. User is trying to use SSH for API operations

## Workflow Patterns

### Pattern 1: Comprehensive GitHub Connectivity Testing
When users ask to "test GitHub connection" or "verify SSH keys", follow this systematic approach:

**Phase 1: Clarify Testing Scope**
- Ask: "Are you testing Git/SSH operations, API access, or both?"
- Clarify: SSH is for Git operations, API tokens are for REST API operations

**Phase 2: SSH Authentication Test**
```bash
# Basic SSH connection test
ssh -T git@github.com
# Expected: "Hi username! You've successfully authenticated..."

# Additional verification
ssh-add -l 2>/dev/null || echo "SSH agent status"
```

**Phase 3: API Token Authentication Test** (if applicable)
```bash
# Test API token if GITHUB_TOKEN is set
# Use curl with Authorization header to /user endpoint
# Expected: Returns user profile with login field
```

**Phase 4: Repository-Specific Testing**
```bash
# Test repository access via SSH
git ls-remote git@github.com:owner/repo.git

# Test clone operation
git clone git@github.com:owner/repo.git /tmp/test-clone
```

**Phase 5: Read/Write Permission Verification** (if needed)
- Create test commit in cloned repository
- Push to verify write permissions
- Clean up test files after verification

**Phase 6: Security Cleanup**
- Unset any temporary environment variables (tokens)
- Remove test directories
- Provide comprehensive test report

### Pattern 2: Repository Creation Workflow
When users need to create repositories:

### Pattern 2: Diagnosing "Repository not found" Errors
When `git clone` fails with "Repository not found" despite successful SSH auth:

1. **Verify repository existence**
   ```bash
   # Using curl with no auth (public repos only)
   curl -s https://api.github.com/repos/owner/repo-name | grep -q '"message":"Not Found"' && echo "Repository doesn't exist"
   ```

2. **Check repository visibility**
   - Public repositories: Accessible to everyone
   - Private repositories: Require explicit access for the SSH key

3. **Verify exact repository name**
   - GitHub repository names are case-sensitive
   - Check for typos or incorrect naming conventions

## Enhanced Testing Methodology

Based on recent troubleshooting experience, here's an enhanced approach:

### Comprehensive Testing Protocol

**Phase 1: Clarification and Scope Definition**
- Ask user: "Are you testing Git/SSH operations, API access, or both?"
- Explain: SSH is for Git operations, API tokens are for REST API operations
- Determine: What specific operations need testing (clone, push, create repo, etc.)

**Phase 2: Systematic Testing**
1. **SSH Authentication**: Test basic SSH connection to GitHub
2. **API Authentication**: Test token validity if provided
3. **Repository Access**: Test access to specific repositories
4. **Operation Verification**: Test actual operations (clone, push, etc.)

**Phase 3: Security Protocols**
- **Token Handling**: Use environment variables temporarily, never store in files
- **Cleanup**: Unset tokens immediately after use
- **Test Data**: Remove any test commits/files from repositories
- **User Confirmation**: Get explicit confirmation before using provided tokens

**Phase 4: Error Resolution**
- **Repository Conflicts**: When "name already exists", verify then clarify user intent
- **Permission Issues**: Distinguish between SSH and API permission problems
- **Authentication Failures**: Test SSH and API separately to isolate issues

**Phase 5: Structured Reporting**
Provide clear report separating:
1. SSH/Git authentication results
2. API authentication results  
3. Repository-specific access results
4. Security status and recommendations

### Key Learnings from Recent Experience

1. **Dual Authentication Systems**: GitHub has completely separate authentication for Git (SSH) vs API (tokens)
2. **Security-First Approach**: Always handle tokens with extreme care, clean up immediately
3. **Clarification Protocol**: When encountering conflicts (like existing repositories), always ask for clarification
4. **Comprehensive Testing**: Test both authentication systems even when user only mentions one
5. **Structured Communication**: Provide clear, separated reports for SSH vs API results

## Common Scenarios and Responses

### Scenario: User provides token for testing
**Response**: 
1. Explain security risks of token exposure
2. Confirm user understands and accepts risks
3. Use token only for required operations
4. Clean up immediately after use
5. Suggest token rotation

### Scenario: "Repository already exists" error
**Response**:
1. Verify repository existence
2. Ask user: Delete and recreate? Use different name? Use existing?
3. Proceed based on clarification
4. Document the resolution approach

### Scenario: SSH works but API operations fail
**Response**:
1. Explain the distinction between SSH and API systems
2. Test API token separately
3. Verify token has required permissions
4. Provide clear explanation of the two systems

## Best Practices Summary

1. **Never assume** SSH access implies API access
2. **Always clarify** when encountering ambiguities
3. **Security first** with token handling
4. **Test systematically** one layer at a time
5. **Document clearly** with separated results
6. **Clean up thoroughly** after testing

## Related Skills

- `github-auth`: Comprehensive authentication setup
- `github-repo-management`: Repository creation and management
- `github-pr-workflow`: Pull request operations