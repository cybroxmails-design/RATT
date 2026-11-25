Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' Forward validated menu arguments (e.g. "copy 3", "copy 1 C:\path\file.docx", "translate fr") to RATT
Set reToken = New RegExp
reToken.Pattern = "^[A-Za-z0-9\-]{1,15}$"
args = ""
If WScript.Arguments.Count <= 4 Then
    For i = 0 To WScript.Arguments.Count - 1
        arg = WScript.Arguments(i)
        If i < 2 Then
            If Not reToken.Test(arg) Then
                WScript.Quit 1
            End If
            args = args & " " & arg
        Else
            ' File or folder path argument (%1): block shell metacharacters and quote safely
            If InStr(arg, """") > 0 Or InStr(arg, "|") > 0 Or InStr(arg, "&") > 0 Or InStr(arg, ";") > 0 Or InStr(arg, "`") > 0 Then
                WScript.Quit 1
            End If
            args = args & " """ & arg & """"
        End If
    Next
Else
    WScript.Quit 1
End If
intStyle = 1
If Trim(args) <> "" Then
    intStyle = 0
End If
WshShell.Run "pythonw -m ratt.main" & args, intStyle, False
