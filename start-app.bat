@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
set "FRONTEND_URL=http://localhost:5173/"
set "API_URL=http://localhost:8000"

echo.
echo ========================================
echo AI Support Resolution Assistant
echo Starting demo environment...
echo ========================================
echo.

where.exe docker >nul 2>&1
if errorlevel 1 goto :docker_unavailable
docker info >nul 2>&1
if errorlevel 1 goto :docker_unavailable
docker compose version >nul 2>&1
if errorlevel 1 goto :docker_unavailable
echo Docker: READY

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $tags = Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 4; $found = $false; foreach ($item in $tags.models) { if ($item.name -eq 'qwen2.5:3b' -or $item.model -eq 'qwen2.5:3b') { $found = $true } }; if ($found) { exit 0 } else { exit 2 } } catch { exit 1 }" >nul 2>&1
set "OLLAMA_CHECK=%ERRORLEVEL%"
if "%OLLAMA_CHECK%"=="1" goto :ollama_unavailable
if not "%OLLAMA_CHECK%"=="0" goto :model_missing
echo Ollama: READY
echo Model: qwen2.5:3b

pushd "%PROJECT_ROOT%"
if errorlevel 1 goto :project_root_error
echo Starting backend services...
docker compose up -d
if errorlevel 1 goto :compose_failed

echo Waiting for FastAPI health check...
for /L %%I in (1,1,20) do (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8000/healthz' -TimeoutSec 1; if ($response.StatusCode -eq 200) { exit 0 } } catch { }; exit 1" >nul 2>&1
    if not errorlevel 1 goto :backend_ready
    timeout /t 2 /nobreak >nul
)
goto :backend_unhealthy

:backend_ready
echo Backend: READY
echo Database: STARTED
echo Ollama: READY
echo Model: qwen2.5:3b
echo.

where.exe npm >nul 2>&1
if errorlevel 1 goto :npm_unavailable

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5173/' -TimeoutSec 2; if ($response.StatusCode -eq 200 -and $response.Content.Contains('AI Support Resolution Assistant')) { exit 0 } else { exit 2 } } catch { exit 1 }" >nul 2>&1
set "FRONTEND_CHECK=%ERRORLEVEL%"
if "%FRONTEND_CHECK%"=="0" goto :frontend_ready
if not "%FRONTEND_CHECK%"=="1" goto :frontend_port_busy

echo Starting React frontend in a separate command window...
start "AI Support Resolution Assistant - Frontend" "%ComSpec%" /k "cd /d ""%PROJECT_ROOT%frontend"" && npm run dev"

echo Waiting for Vite to become ready...
for /L %%I in (1,1,20) do (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5173/' -TimeoutSec 1; if ($response.StatusCode -eq 200 -and $response.Content.Contains('AI Support Resolution Assistant')) { exit 0 } } catch { }; exit 1" >nul 2>&1
    if not errorlevel 1 goto :frontend_ready
    timeout /t 2 /nobreak >nul
)
echo.
echo ERROR: The frontend did not become ready at %FRONTEND_URL% within 40 seconds.
echo Check the separate frontend command window for npm or Vite errors.
popd
goto :failure

:frontend_ready
echo Frontend: READY
start "" "%FRONTEND_URL%"
echo.
echo ========================================
echo AI SUPPORT RESOLUTION ASSISTANT READY
echo ========================================
echo.
echo Frontend:
echo %FRONTEND_URL%
echo.
echo API:
echo %API_URL%/docs
echo.
echo Health:
echo %API_URL%/healthz
echo.
echo Press Ctrl+C in the frontend window to stop the React dev server.
echo.
echo To stop backend services:
echo docker compose down
echo.
echo ========================================
popd
pause
exit /b 0

:frontend_port_busy
echo.
echo ERROR: Port 5173 is responding, but it does not appear to be this project.
echo Close or move the other service, then run this script again.
popd
goto :failure

:backend_unhealthy
echo.
echo ERROR: FastAPI did not become healthy within 60 seconds.
echo.
echo Docker Compose status:
docker compose ps
echo.
echo Recent API logs:
docker compose logs --tail 80 api
popd
goto :failure

:compose_failed
echo.
echo ERROR: Docker Compose could not start the backend services.
echo Check the Docker Desktop window and the output above.
popd
goto :failure

:project_root_error
echo.
echo ERROR: Could not access the project directory:
echo %PROJECT_ROOT%
goto :failure

:npm_unavailable
echo.
echo ERROR: npm was not found on PATH. Install Node.js with npm, then retry.
popd
goto :failure

:docker_unavailable
echo.
echo ERROR: Docker is unavailable. Please start Docker Desktop, wait for it to finish starting, and retry.
goto :failure

:ollama_unavailable
echo.
echo Ollama is not reachable. Please make sure Ollama is running.
goto :failure

:model_missing
echo.
echo The qwen2.5:3b model is not present in Ollama.
echo Run this command, then start the demo again:
echo ollama pull qwen2.5:3b
goto :failure

:failure
echo.
pause
exit /b 1
