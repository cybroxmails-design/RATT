Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' Forward validated menu arguments (e.g. "copy 3", "translate fr") to RATT
Set re = New RegExp
re.Pattern = "^[A-Za-z0-9\-]{1,10}$"
args = ""
If WScript.Arguments.Count <= 3 Then
    For i = 0 To WScript.Arguments.Count - 1
        arg = WScript.Arguments(i)
        If Not re.Test(arg) Then
            WScript.Quit 1
        End If
        args = args & " " & arg
    Next
Else
    WScript.Quit 1
End If
intStyle = 1
If Trim(args) <> "" Then
    intStyle = 0
End If
WshShell.Run "pythonw -m ratt.main" & args, intStyle, False
