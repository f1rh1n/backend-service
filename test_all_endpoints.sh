#!/bin/bash

# Script to test all API endpoints
BASE_URL="http://localhost:8000"

echo "==================================="
echo "Testing Document Management API"
echo "==================================="
echo ""

# 1. Test Health Endpoint
echo "1. Testing Health Endpoint..."
curl -s $BASE_URL/health | jq '.'
echo ""

# 2. Register User
echo "2. Testing User Registration..."
REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "securepass123",
    "first_name": "John",
    "last_name": "Doe"
  }')
echo $REGISTER_RESPONSE | jq '.'
echo ""

# 3. Login
echo "3. Testing Login..."
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser@example.com&password=securepass123")
echo $LOGIN_RESPONSE | jq '.'

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')
echo "Access Token: ${ACCESS_TOKEN:0:50}..."
echo ""

# 4. Get Current User
echo "4. Testing Get Current User..."
curl -s $BASE_URL/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 5. Upload Document
echo "5. Testing Document Upload..."
echo "This is a test document" > /tmp/test_doc.txt
UPLOAD_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/documents \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "title=Test Document" \
  -F "description=This is a test document for API testing" \
  -F "tags=test" \
  -F "tags=demo" \
  -F "file=@/tmp/test_doc.txt")
echo $UPLOAD_RESPONSE | jq '.'

DOC_ID=$(echo $UPLOAD_RESPONSE | jq -r '.id')
echo "Document ID: $DOC_ID"
echo ""

# 6. List Documents
echo "6. Testing List Documents..."
curl -s "$BASE_URL/api/v1/documents?page=1&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 7. Get Document Metadata
echo "7. Testing Get Document Metadata..."
curl -s $BASE_URL/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 8. Update Document Metadata
echo "8. Testing Update Document Metadata..."
curl -s -X PUT $BASE_URL/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Test Document",
    "description": "Updated description"
  }' | jq '.'
echo ""

# 9. Get Document Versions
echo "9. Testing Get Document Versions..."
curl -s $BASE_URL/api/v1/documents/$DOC_ID/versions \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 10. Download Document
echo "10. Testing Download Document..."
DOWNLOAD_RESPONSE=$(curl -s $BASE_URL/api/v1/documents/$DOC_ID/download \
  -H "Authorization: Bearer $ACCESS_TOKEN")
echo $DOWNLOAD_RESPONSE | jq '.'
echo ""

# 11. Upload New Version
echo "11. Testing Upload New Version..."
echo "This is version 2 of the document" > /tmp/test_doc_v2.txt
curl -s -X POST $BASE_URL/api/v1/documents/$DOC_ID/upload-version \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/tmp/test_doc_v2.txt" | jq '.'
echo ""

# 12. Register Second User for Permission Testing
echo "12. Registering Second User for Permission Testing..."
REGISTER2_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "password": "securepass123",
    "first_name": "Jane",
    "last_name": "Smith"
  }')
echo $REGISTER2_RESPONSE | jq '.'

USER2_ID=$(echo $REGISTER2_RESPONSE | jq -r '.id')
echo "Second User ID: $USER2_ID"
echo ""

# 13. Share Document
echo "13. Testing Share Document..."
curl -s -X POST $BASE_URL/api/v1/documents/$DOC_ID/permissions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER2_ID\",
    \"role\": \"READ\"
  }" | jq '.'
echo ""

# 14. List Document Permissions
echo "14. Testing List Document Permissions..."
curl -s $BASE_URL/api/v1/documents/$DOC_ID/permissions \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 15. Update Permission
echo "15. Testing Update Permission..."
curl -s -X PUT $BASE_URL/api/v1/documents/$DOC_ID/permissions/$USER2_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "EDIT"
  }' | jq '.'
echo ""

# 16. Test Refresh Token
echo "16. Testing Refresh Token..."
curl -s -X POST $BASE_URL/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}" | jq '.'
echo ""

# 17. Search Documents
echo "17. Testing Search Documents..."
curl -s "$BASE_URL/api/v1/documents?search=Updated&page=1&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 18. Filter by Tags
echo "18. Testing Filter by Tags..."
curl -s "$BASE_URL/api/v1/documents?tags=test&page=1&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 19. Revoke Permission
echo "19. Testing Revoke Permission..."
curl -s -X DELETE $BASE_URL/api/v1/documents/$DOC_ID/permissions/$USER2_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 20. Delete Document
echo "20. Testing Delete Document (Soft Delete)..."
curl -s -X DELETE $BASE_URL/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.'
echo ""

# 21. Logout
echo "21. Testing Logout..."
curl -s -X POST $BASE_URL/api/v1/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}" | jq '.'
echo ""

echo "==================================="
echo "All Tests Complete!"
echo "==================================="
