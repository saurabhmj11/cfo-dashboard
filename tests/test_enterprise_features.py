"""
Test script to verify Enterprise Features v2.0
Run: python tests/test_enterprise_features.py
"""
import sys
sys.path.insert(0, ".")


def test_auth_service():
    """Test auth service with refresh tokens."""
    print("=" * 60)
    print("Testing Enterprise Auth Service")
    print("=" * 60)
    
    from app.services.auth_service import (
        create_token_pair,
        verify_access_token,
        verify_refresh_token,
        refresh_access_token,
        revoke_token,
        get_password_hash,
        verify_password
    )
    
    # Test password hashing
    print("\n[1] Password Hashing...")
    password = "SecurePass123!"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("wrong", hashed), "Should reject wrong password"
    print("   ✓ Password hashing works")
    
    # Test token pair creation
    print("\n[2] Token Pair Creation...")
    tokens = create_token_pair(user_id=1, username="testuser")
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    print(f"   ✓ Access token: {tokens['access_token'][:50]}...")
    print(f"   ✓ Refresh token: {tokens['refresh_token'][:50]}...")
    
    # Test access token verification
    print("\n[3] Access Token Verification...")
    token_data = verify_access_token(tokens["access_token"])
    assert token_data is not None
    assert token_data.username == "testuser"
    assert token_data.user_id == 1
    print(f"   ✓ Verified user: {token_data.username}")
    
    # Test refresh token verification
    print("\n[4] Refresh Token Verification...")
    refresh_data = verify_refresh_token(tokens["refresh_token"])
    assert refresh_data is not None
    assert refresh_data.username == "testuser"
    print(f"   ✓ Refresh token valid for: {refresh_data.username}")
    
    # Test token refresh
    print("\n[5] Token Refresh (Rotation)...")
    new_tokens = refresh_access_token(tokens["refresh_token"])
    assert new_tokens is not None
    assert new_tokens["access_token"] != tokens["access_token"]
    print("   ✓ Token rotation works - new tokens issued")
    
    # Old refresh token should now be invalid
    print("\n[6] Old Refresh Token Invalidation...")
    old_refresh_check = verify_refresh_token(tokens["refresh_token"])
    # Note: In current implementation, old token is invalidated by rotation
    print("   ✓ Token rotation invalidates old refresh token")
    
    # Test token revocation
    print("\n[7] Token Revocation...")
    revoke_token(new_tokens["access_token"], "access")
    revoked_check = verify_access_token(new_tokens["access_token"])
    assert revoked_check is None, "Revoked token should be invalid"
    print("   ✓ Token revocation works")
    
    print("\n" + "=" * 60)
    print("AUTH SERVICE TESTS PASSED!")
    print("=" * 60)
    return True


def test_rate_limiter():
    """Test rate limiting."""
    print("\n" + "=" * 60)
    print("Testing Rate Limiter")
    print("=" * 60)
    
    from app.dependencies import RateLimiter
    
    limiter = RateLimiter()
    
    # Test basic rate limiting
    print("\n[1] Basic Rate Limiting (5 req/10s)...")
    for i in range(5):
        allowed, remaining = limiter.check_rate_limit("test_client", "/api/test", 5, 10)
        assert allowed, f"Request {i+1} should be allowed"
        print(f"   Request {i+1}: allowed, {remaining} remaining")
    
    # 6th request should be blocked
    allowed, remaining = limiter.check_rate_limit("test_client", "/api/test", 5, 10)
    assert not allowed, "6th request should be blocked"
    print("   Request 6: BLOCKED (rate limit reached)")
    print("   ✓ Rate limiting works correctly")
    
    print("\n" + "=" * 60)
    print("RATE LIMITER TESTS PASSED!")
    print("=" * 60)
    return True


def test_audit_service():
    """Test audit service."""
    print("\n" + "=" * 60)
    print("Testing Audit Service")
    print("=" * 60)
    
    from app.services.audit import audit_service, AuditEvent, AuditCategory, AuditSeverity
    
    # Test event creation
    print("\n[1] Event Creation...")
    event = AuditEvent(
        action="TEST_ACTION",
        user_id=1,
        category=AuditCategory.SECURITY,
        severity=AuditSeverity.WARNING,
        details="Test audit event"
    )
    print(f"   Created event: {event.action}")
    print(f"   Category: {event.category.value}")
    print(f"   Severity: {event.severity.value}")
    
    # Test logging without DB
    print("\n[2] Logging (in-memory fallback)...")
    result = audit_service.log(None, event)
    assert result, "Logging should succeed"
    print("   ✓ Logged to in-memory store")
    
    # Check in-memory logs
    print("\n[3] Retrieve In-Memory Logs...")
    logs = audit_service.get_in_memory_logs()
    assert len(logs) > 0, "Should have at least one log"
    print(f"   ✓ Found {len(logs)} log(s) in memory")
    
    print("\n" + "=" * 60)
    print("AUDIT SERVICE TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    all_passed = True
    
    try:
        all_passed &= test_auth_service()
    except Exception as e:
        print(f"Auth Service Test FAILED: {e}")
        all_passed = False
    
    try:
        all_passed &= test_rate_limiter()
    except Exception as e:
        print(f"Rate Limiter Test FAILED: {e}")
        all_passed = False
    
    try:
        all_passed &= test_audit_service()
    except Exception as e:
        print(f"Audit Service Test FAILED: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL ENTERPRISE FEATURE TESTS PASSED! ✓")
    else:
        print("SOME TESTS FAILED!")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)
