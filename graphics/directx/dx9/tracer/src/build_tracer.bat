@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul 2>&1
echo Compiling d3d9_trace_main.c...
cl.exe /nologo /O2 /W3 /c /D "WIN32" /D "NDEBUG" d3d9_trace_main.c
if errorlevel 1 goto :error
echo Compiling d3d9_trace_wrapper.c...
cl.exe /nologo /O2 /W3 /c /D "WIN32" /D "NDEBUG" d3d9_trace_wrapper.c
if errorlevel 1 goto :error
echo Compiling d3d9_trace_device.c...
cl.exe /nologo /O2 /W3 /c /D "WIN32" /D "NDEBUG" d3d9_trace_device.c
if errorlevel 1 goto :error
echo Linking d3d9.dll...
link.exe /nologo /DLL /DEF:d3d9.def /OUT:d3d9.dll d3d9_trace_main.obj d3d9_trace_wrapper.obj d3d9_trace_device.obj kernel32.lib user32.lib
if errorlevel 1 goto :error
echo === Build successful ===
if not exist "..\bin" mkdir "..\bin"
copy /Y d3d9.dll ..\bin\d3d9.dll >nul
del *.obj *.lib *.exp d3d9.dll 2>nul
echo Deployed to bin\d3d9.dll
exit /b 0
:error
echo === BUILD FAILED ===
exit /b 1
