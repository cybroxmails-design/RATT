# RATT v2 Android R8 / ProGuard Hardening & Anti-Reverse Engineering Rules
# Enforces symbol obfuscation, package flattening, debug metadata stripping, and log removal.

-optimizationpasses 5
-allowaccessmodification
-repackageclasses 'o'
-overloadaggressively
-renamesourcefileattribute SourceFile

# Strip debug line numbers and verbose logging from release bytecode
-assumenosideeffects class android.util.Log {
    public static boolean isLoggable(java.lang.String, int);
    public static int v(...);
    public static int d(...);
    public static int i(...);
}

# Keep only Android OS Manifest-registered entrypoints (obfuscate all internal logic & fields)
-keep public class com.cybrox.ratt.MainActivity
-keep public class com.cybrox.ratt.FloatingAssistService
-keep public class com.cybrox.ratt.RattAccessibilityService
-keep public class com.cybrox.ratt.RattIME
-keep public class com.cybrox.ratt.ProcessTextActivity
-keep public class com.cybrox.ratt.SaveClipActivity

-dontwarn com.cybrox.ratt.**
