@echo off
REM ECR Backend Image Upload Script (Windows)

echo === FaaS Backend ECR Upload ===
echo.

REM 1. Check AWS Account ID
echo [1/6] Checking AWS Account ID...
for /f "delims=" %%i in ('aws sts get-caller-identity --query Account --output text 2^>nul') do set AWS_ACCOUNT_ID=%%i

if "%AWS_ACCOUNT_ID%"=="" (
    echo [ERROR] AWS CLI configuration required.
    echo Run 'aws configure' first.
    exit /b 1
)

echo [OK] AWS Account ID: %AWS_ACCOUNT_ID%
echo.

REM Variables
set AWS_REGION=ap-northeast-2
set REPO_NAME=faas-backend
set IMAGE_NAME=faas-backend
set ECR_URL=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com

REM 2. ECR Login
echo [2/6] Logging in to ECR...
aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin %ECR_URL%

if %ERRORLEVEL% neq 0 (
    echo [ERROR] ECR login failed
    exit /b 1
)

echo [OK] ECR login successful
echo.

REM 3. Check/Create ECR Repository
echo [3/6] Checking ECR repository...
aws ecr describe-repositories --repository-names %REPO_NAME% --region %AWS_REGION% >nul 2>&1

if %ERRORLEVEL% neq 0 (
    echo Repository not found. Creating...
    aws ecr create-repository --repository-name %REPO_NAME% --region %AWS_REGION% --image-scanning-configuration scanOnPush=true
    echo [OK] Repository created
) else (
    echo [OK] Repository already exists
)
echo.

REM 4. Build Docker Image
echo [4/6] Building Docker image...
cd /d %~dp0
docker build -t %IMAGE_NAME%:latest .

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Image build failed
    exit /b 1
)

echo [OK] Image build successful
echo.

REM 5. Tag Image
echo [5/6] Tagging image...
docker tag %IMAGE_NAME%:latest %ECR_URL%/%REPO_NAME%:latest
echo [OK] Image tagged
echo.

REM 6. Push to ECR
echo [6/6] Pushing to ECR...
docker push %ECR_URL%/%REPO_NAME%:latest

if %ERRORLEVEL% neq 0 (
    echo [ERROR] ECR push failed
    exit /b 1
)

echo.
echo ================================
echo [OK] ECR Upload Complete!
echo ================================
echo.
echo Image URL:
echo %ECR_URL%/%REPO_NAME%:latest
echo.
echo Share this URL with your infrastructure engineer.

pause
