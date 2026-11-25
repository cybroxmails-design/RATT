import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
XCODEPROJ_DIR = os.path.join(PROJECT_DIR, "Ratt.xcodeproj")
SCHEMES_DIR = os.path.join(XCODEPROJ_DIR, "xcshareddata", "xcschemes")
os.makedirs(SCHEMES_DIR, exist_ok=True)
PBXPROJ_PATH = os.path.join(XCODEPROJ_DIR, "project.pbxproj")
SCHEME_PATH = os.path.join(SCHEMES_DIR, "RattApp.xcscheme")

content = """// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 56;
	objects = {

/* Begin PBXBuildFile section */
		A10000000000000000000001 /* RattApp.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000001 /* RattApp.swift */; };
		A10000000000000000000002 /* ContentView.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000002 /* ContentView.swift */; };
		A10000000000000000000003 /* AppGroupDataManager.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000003 /* AppGroupDataManager.swift */; };
		A10000000000000000000004 /* Models.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000004 /* Models.swift */; };
		A10000000000000000000005 /* KeychainSlotStore.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000005 /* KeychainSlotStore.swift */; };
		A10000000000000000000006 /* RattSecurityGuard.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000006 /* RattSecurityGuard.swift */; };
		A10000000000000000000007 /* RattKeyboard.appex in Embed App Extensions */ = {isa = PBXBuildFile; fileRef = B10000000000000000000020 /* RattKeyboard.appex */; settings = {ATTRIBUTES = (RemoveHeadersOnCopy, ); }; };
		A10000000000000000000008 /* Assets.xcassets in Resources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000008 /* Assets.xcassets */; };
		A10000000000000000000009 /* SecurityHardening.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000009 /* SecurityHardening.swift */; };
		A10000000000000000000010 /* RattShareExtension.appex in Embed App Extensions */ = {isa = PBXBuildFile; fileRef = B30000000000000000000020 /* RattShareExtension.appex */; settings = {ATTRIBUTES = (RemoveHeadersOnCopy, ); }; };
		A10000000000000000000013 /* PrivacyInfo.xcprivacy in Resources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000013 /* PrivacyInfo.xcprivacy */; };
		A20000000000000000000001 /* RattKeyboardViewController.swift in Sources */ = {isa = PBXBuildFile; fileRef = B20000000000000000000001 /* RattKeyboardViewController.swift */; };
		A20000000000000000000002 /* KeyboardViewController.swift in Sources */ = {isa = PBXBuildFile; fileRef = B20000000000000000000002 /* KeyboardViewController.swift */; };
		A20000000000000000000003 /* AppGroupDataManager.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000003 /* AppGroupDataManager.swift */; };
		A20000000000000000000004 /* Models.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000004 /* Models.swift */; };
		A20000000000000000000005 /* KeychainSlotStore.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000005 /* KeychainSlotStore.swift */; };
		A20000000000000000000006 /* RattSecurityGuard.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000006 /* RattSecurityGuard.swift */; };
		A20000000000000000000009 /* SecurityHardening.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000009 /* SecurityHardening.swift */; };
		A20000000000000000000013 /* PrivacyInfo.xcprivacy in Resources */ = {isa = PBXBuildFile; fileRef = B20000000000000000000013 /* PrivacyInfo.xcprivacy */; };
		A30000000000000000000001 /* ShareViewController.swift in Sources */ = {isa = PBXBuildFile; fileRef = B30000000000000000000001 /* ShareViewController.swift */; };
		A30000000000000000000002 /* AppGroupDataManager.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000003 /* AppGroupDataManager.swift */; };
		A30000000000000000000003 /* Models.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000004 /* Models.swift */; };
		A30000000000000000000005 /* KeychainSlotStore.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000005 /* KeychainSlotStore.swift */; };
		A30000000000000000000006 /* RattSecurityGuard.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000006 /* RattSecurityGuard.swift */; };
		A30000000000000000000009 /* SecurityHardening.swift in Sources */ = {isa = PBXBuildFile; fileRef = B10000000000000000000009 /* SecurityHardening.swift */; };
		A30000000000000000000013 /* PrivacyInfo.xcprivacy in Resources */ = {isa = PBXBuildFile; fileRef = B30000000000000000000013 /* PrivacyInfo.xcprivacy */; };
/* End PBXBuildFile section */

/* Begin PBXContainerItemProxy section */
		C00000000000000000000001 /* PBXContainerItemProxy */ = {
			isa = PBXContainerItemProxy;
			containerPortal = AA0000000000000000000001 /* Project object */;
			proxyType = 1;
			remoteGlobalIDString = E00000000000000000000002 /* RattKeyboard */;
			remoteInfo = RattKeyboard;
		};
		C00000000000000000000002 /* PBXContainerItemProxy */ = {
			isa = PBXContainerItemProxy;
			containerPortal = AA0000000000000000000001 /* Project object */;
			proxyType = 1;
			remoteGlobalIDString = E00000000000000000000003 /* RattShareExtension */;
			remoteInfo = RattShareExtension;
		};
/* End PBXContainerItemProxy section */

/* Begin PBXCopyFilesBuildPhase section */
		E10000000000000000000001 /* Embed App Extensions */ = {
			isa = PBXCopyFilesBuildPhase;
			buildActionMask = 2147483647;
			dstPath = "";
			dstSubfolderSpec = 13;
			files = (
				A10000000000000000000007 /* RattKeyboard.appex in Embed App Extensions */,
				A10000000000000000000010 /* RattShareExtension.appex in Embed App Extensions */,
			);
			name = "Embed App Extensions";
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXCopyFilesBuildPhase section */

/* Begin PBXFileReference section */
		B10000000000000000000001 /* RattApp.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = RattApp.swift; sourceTree = "<group>"; };
		B10000000000000000000002 /* ContentView.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ContentView.swift; sourceTree = "<group>"; };
		B10000000000000000000003 /* AppGroupDataManager.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = AppGroupDataManager.swift; sourceTree = "<group>"; };
		B10000000000000000000004 /* Models.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = Models.swift; sourceTree = "<group>"; };
		B10000000000000000000005 /* KeychainSlotStore.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = KeychainSlotStore.swift; sourceTree = "<group>"; };
		B10000000000000000000006 /* RattSecurityGuard.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = RattSecurityGuard.swift; sourceTree = "<group>"; };
		B10000000000000000000008 /* Assets.xcassets */ = {isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = "<group>"; };
		B10000000000000000000009 /* SecurityHardening.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = SecurityHardening.swift; sourceTree = "<group>"; };
		B10000000000000000000010 /* RattApp.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = RattApp.app; sourceTree = BUILT_PRODUCTS_DIR; };
		B10000000000000000000011 /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };
		B10000000000000000000012 /* RattApp.entitlements */ = {isa = PBXFileReference; lastKnownFileType = text.plist.entitlements; path = RattApp.entitlements; sourceTree = "<group>"; };
		B10000000000000000000013 /* PrivacyInfo.xcprivacy */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = PrivacyInfo.xcprivacy; sourceTree = "<group>"; };
		B10000000000000000000020 /* RattKeyboard.appex */ = {isa = PBXFileReference; explicitFileType = "wrapper.app-extension"; includeInIndex = 0; path = RattKeyboard.appex; sourceTree = BUILT_PRODUCTS_DIR; };
		B20000000000000000000001 /* RattKeyboardViewController.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = RattKeyboardViewController.swift; sourceTree = "<group>"; };
		B20000000000000000000002 /* KeyboardViewController.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = KeyboardViewController.swift; sourceTree = "<group>"; };
		B20000000000000000000011 /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };
		B20000000000000000000012 /* RattKeyboard.entitlements */ = {isa = PBXFileReference; lastKnownFileType = text.plist.entitlements; path = RattKeyboard.entitlements; sourceTree = "<group>"; };
		B20000000000000000000013 /* PrivacyInfo.xcprivacy */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = PrivacyInfo.xcprivacy; sourceTree = "<group>"; };
		B30000000000000000000001 /* ShareViewController.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ShareViewController.swift; sourceTree = "<group>"; };
		B30000000000000000000011 /* Info.plist */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; };
		B30000000000000000000012 /* RattShareExtension.entitlements */ = {isa = PBXFileReference; lastKnownFileType = text.plist.entitlements; path = RattShareExtension.entitlements; sourceTree = "<group>"; };
		B30000000000000000000013 /* PrivacyInfo.xcprivacy */ = {isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = PrivacyInfo.xcprivacy; sourceTree = "<group>"; };
		B30000000000000000000020 /* RattShareExtension.appex */ = {isa = PBXFileReference; explicitFileType = "wrapper.app-extension"; includeInIndex = 0; path = RattShareExtension.appex; sourceTree = BUILT_PRODUCTS_DIR; };
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		F10000000000000000000001 /* Frameworks */ = {
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
		F20000000000000000000001 /* Frameworks */ = {
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
		F30000000000000000000001 /* Frameworks */ = {
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		D00000000000000000000000 = {
			isa = PBXGroup;
			children = (
				D00000000000000000000001 /* RattApp */,
				D00000000000000000000002 /* RattKeyboard */,
				D00000000000000000000005 /* RattShareExtension */,
				D00000000000000000000003 /* Shared */,
				D00000000000000000000004 /* Products */,
			);
			sourceTree = "<group>";
		};
		D00000000000000000000001 /* RattApp */ = {
			isa = PBXGroup;
			children = (
				B10000000000000000000001 /* RattApp.swift */,
				B10000000000000000000002 /* ContentView.swift */,
				B10000000000000000000008 /* Assets.xcassets */,
				B10000000000000000000011 /* Info.plist */,
				B10000000000000000000012 /* RattApp.entitlements */,
				B10000000000000000000013 /* PrivacyInfo.xcprivacy */,
			);
			path = RattApp;
			sourceTree = "<group>";
		};
		D00000000000000000000002 /* RattKeyboard */ = {
			isa = PBXGroup;
			children = (
				B20000000000000000000001 /* RattKeyboardViewController.swift */,
				B20000000000000000000002 /* KeyboardViewController.swift */,
				B10000000000000000000005 /* KeychainSlotStore.swift */,
				B10000000000000000000006 /* RattSecurityGuard.swift */,
				B20000000000000000000011 /* Info.plist */,
				B20000000000000000000012 /* RattKeyboard.entitlements */,
				B20000000000000000000013 /* PrivacyInfo.xcprivacy */,
			);
			path = RattKeyboard;
			sourceTree = "<group>";
		};
		D00000000000000000000005 /* RattShareExtension */ = {
			isa = PBXGroup;
			children = (
				B30000000000000000000001 /* ShareViewController.swift */,
				B30000000000000000000011 /* Info.plist */,
				B30000000000000000000012 /* RattShareExtension.entitlements */,
				B30000000000000000000013 /* PrivacyInfo.xcprivacy */,
			);
			path = RattShareExtension;
			sourceTree = "<group>";
		};
		D00000000000000000000003 /* Shared */ = {
			isa = PBXGroup;
			children = (
				B10000000000000000000003 /* AppGroupDataManager.swift */,
				B10000000000000000000004 /* Models.swift */,
				B10000000000000000000009 /* SecurityHardening.swift */,
			);
			path = Shared;
			sourceTree = "<group>";
		};
		D00000000000000000000004 /* Products */ = {
			isa = PBXGroup;
			children = (
				B10000000000000000000010 /* RattApp.app */,
				B10000000000000000000020 /* RattKeyboard.appex */,
				B30000000000000000000020 /* RattShareExtension.appex */,
			);
			name = Products;
			sourceTree = "<group>";
		};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		E00000000000000000000001 /* RattApp */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = C10000000000000000000002 /* Build configuration list for PBXNativeTarget "RattApp" */;
			buildPhases = (
				FA0000000000000000000001 /* Sources */,
				F10000000000000000000001 /* Frameworks */,
				F00000000000000000000001 /* Resources */,
				E10000000000000000000001 /* Embed App Extensions */,
			);
			buildRules = (
			);
			dependencies = (
				D10000000000000000000001 /* PBXTargetDependency */,
				D10000000000000000000002 /* PBXTargetDependency */,
			);
			name = RattApp;
			productName = RattApp;
			productReference = B10000000000000000000010 /* RattApp.app */;
			productType = "com.apple.product-type.application";
		};
		E00000000000000000000002 /* RattKeyboard */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = C20000000000000000000002 /* Build configuration list for PBXNativeTarget "RattKeyboard" */;
			buildPhases = (
				FA0000000000000000000002 /* Sources */,
				F20000000000000000000001 /* Frameworks */,
				F00000000000000000000002 /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = RattKeyboard;
			productName = RattKeyboard;
			productReference = B10000000000000000000020 /* RattKeyboard.appex */;
			productType = "com.apple.product-type.app-extension";
		};
		E00000000000000000000003 /* RattShareExtension */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = C30000000000000000000002 /* Build configuration list for PBXNativeTarget "RattShareExtension" */;
			buildPhases = (
				FA0000000000000000000003 /* Sources */,
				F30000000000000000000001 /* Frameworks */,
				F00000000000000000000003 /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = RattShareExtension;
			productName = RattShareExtension;
			productReference = B30000000000000000000020 /* RattShareExtension.appex */;
			productType = "com.apple.product-type.app-extension";
		};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		AA0000000000000000000001 /* Project object */ = {
			isa = PBXProject;
			attributes = {
				BuildIndependentTargetsInParallel = 1;
				LastUpgradeCheck = 1500;
				TargetAttributes = {
					E00000000000000000000001 = {
						CreatedOnToolsVersion = 15.0;
					};
					E00000000000000000000002 = {
						CreatedOnToolsVersion = 15.0;
					};
					E00000000000000000000003 = {
						CreatedOnToolsVersion = 15.0;
					};
				};
			};
			buildConfigurationList = AA0000000000000000000002 /* Build configuration list for PBXProject "Ratt" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = D00000000000000000000000;
			productRefGroup = D00000000000000000000004 /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				E00000000000000000000001 /* RattApp */,
				E00000000000000000000002 /* RattKeyboard */,
				E00000000000000000000003 /* RattShareExtension */,
			);
		};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		F00000000000000000000001 /* Resources */ = {
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				A10000000000000000000008 /* Assets.xcassets in Resources */,
				A10000000000000000000013 /* PrivacyInfo.xcprivacy in Resources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
		F00000000000000000000002 /* Resources */ = {
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				A20000000000000000000013 /* PrivacyInfo.xcprivacy in Resources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
		F00000000000000000000003 /* Resources */ = {
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				A30000000000000000000013 /* PrivacyInfo.xcprivacy in Resources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		FA0000000000000000000001 /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				A10000000000000000000001 /* RattApp.swift in Sources */,
				A10000000000000000000002 /* ContentView.swift in Sources */,
				A10000000000000000000003 /* AppGroupDataManager.swift in Sources */,
				A10000000000000000000004 /* Models.swift in Sources */,
				A10000000000000000000005 /* KeychainSlotStore.swift in Sources */,
				A10000000000000000000006 /* RattSecurityGuard.swift in Sources */,
				A10000000000000000000009 /* SecurityHardening.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
		FA0000000000000000000002 /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				A20000000000000000000001 /* RattKeyboardViewController.swift in Sources */,
				A20000000000000000000002 /* KeyboardViewController.swift in Sources */,
				A20000000000000000000003 /* AppGroupDataManager.swift in Sources */,
				A20000000000000000000004 /* Models.swift in Sources */,
				A20000000000000000000005 /* KeychainSlotStore.swift in Sources */,
				A20000000000000000000006 /* RattSecurityGuard.swift in Sources */,
				A20000000000000000000009 /* SecurityHardening.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
		FA0000000000000000000003 /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				A30000000000000000000001 /* ShareViewController.swift in Sources */,
				A30000000000000000000002 /* AppGroupDataManager.swift in Sources */,
				A30000000000000000000003 /* Models.swift in Sources */,
				A30000000000000000000005 /* KeychainSlotStore.swift in Sources */,
				A30000000000000000000006 /* RattSecurityGuard.swift in Sources */,
				A30000000000000000000009 /* SecurityHardening.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXSourcesBuildPhase section */

/* Begin PBXTargetDependency section */
		D10000000000000000000001 /* PBXTargetDependency */ = {
			isa = PBXTargetDependency;
			target = E00000000000000000000002 /* RattKeyboard */;
			targetProxy = C00000000000000000000001 /* PBXContainerItemProxy */;
		};
		D10000000000000000000002 /* PBXTargetDependency */ = {
			isa = PBXTargetDependency;
			target = E00000000000000000000003 /* RattShareExtension */;
			targetProxy = C00000000000000000000002 /* PBXContainerItemProxy */;
		};
/* End PBXTargetDependency section */

/* Begin XCBuildConfiguration section */
		BC0000000000000000000001 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = dwarf;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_TESTABILITY = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = NO;
				GCC_DYNAMIC_NO_PIC = NO;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_OPTIMIZATION_LEVEL = 0;
				GCC_PREPROCESSOR_DEFINITIONS = (
					"DEBUG=1",
					"$(inherited)",
				);
				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
				MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
				MTL_FAST_MATH = YES;
				ONLY_ACTIVE_ARCH = YES;
				SDKROOT = iphoneos;
				SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
				SWIFT_VERSION = 5.0;
			};
			name = Debug;
		};
		BC0000000000000000000002 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				ENABLE_NS_ASSERTIONS = NO;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = NO;
				GCC_NO_COMMON_BLOCKS = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
				MTL_ENABLE_DEBUG_INFO = NO;
				MTL_FAST_MATH = YES;
				SDKROOT = iphoneos;
				SWIFT_COMPILATION_MODE = wholemodule;
				SWIFT_OPTIMIZATION_LEVEL = "-O";
				SWIFT_VERSION = 5.0;
				VALIDATE_PRODUCT = YES;
			};
			name = Release;
		};
		BC1000000000000000000001 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				CODE_SIGN_ENTITLEMENTS = RattApp/RattApp.entitlements;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 2;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = RattApp/Info.plist;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 2.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.cybrox.ratt;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Debug;
		};
		BC1000000000000000000002 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				CODE_SIGN_ENTITLEMENTS = RattApp/RattApp.entitlements;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 2;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = RattApp/Info.plist;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 2.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.cybrox.ratt;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Release;
		};
		BC2000000000000000000001 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				APPLICATION_EXTENSION_API_ONLY = YES;
				CODE_SIGN_ENTITLEMENTS = RattKeyboard/RattKeyboard.entitlements;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 2;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = RattKeyboard/Info.plist;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
					"@executable_path/../../Frameworks",
				);
				MARKETING_VERSION = 2.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.cybrox.ratt.RattKeyboard;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SKIP_INSTALL = YES;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Debug;
		};
		BC2000000000000000000002 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				APPLICATION_EXTENSION_API_ONLY = YES;
				CODE_SIGN_ENTITLEMENTS = RattKeyboard/RattKeyboard.entitlements;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 2;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = RattKeyboard/Info.plist;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
					"@executable_path/../../Frameworks",
				);
				MARKETING_VERSION = 2.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.cybrox.ratt.RattKeyboard;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SKIP_INSTALL = YES;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Release;
		};
		BC3000000000000000000001 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				APPLICATION_EXTENSION_API_ONLY = YES;
				CODE_SIGN_ENTITLEMENTS = RattShareExtension/RattShareExtension.entitlements;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 2;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = RattShareExtension/Info.plist;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
					"@executable_path/../../Frameworks",
				);
				MARKETING_VERSION = 2.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.cybrox.ratt.RattShareExtension;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SKIP_INSTALL = YES;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Debug;
		};
		BC3000000000000000000002 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				APPLICATION_EXTENSION_API_ONLY = YES;
				CODE_SIGN_ENTITLEMENTS = RattShareExtension/RattShareExtension.entitlements;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 2;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = RattShareExtension/Info.plist;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
					"@executable_path/../../Frameworks",
				);
				MARKETING_VERSION = 2.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.cybrox.ratt.RattShareExtension;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SKIP_INSTALL = YES;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Release;
		};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		AA0000000000000000000002 /* Build configuration list for PBXProject "Ratt" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				BC0000000000000000000001 /* Debug */,
				BC0000000000000000000002 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
		C10000000000000000000002 /* Build configuration list for PBXNativeTarget "RattApp" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				BC1000000000000000000001 /* Debug */,
				BC1000000000000000000002 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
		C20000000000000000000002 /* Build configuration list for PBXNativeTarget "RattKeyboard" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				BC2000000000000000000001 /* Debug */,
				BC2000000000000000000002 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
		C30000000000000000000002 /* Build configuration list for PBXNativeTarget "RattShareExtension" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				BC3000000000000000000001 /* Debug */,
				BC3000000000000000000002 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
/* End XCConfigurationList section */

	};
	rootObject = AA0000000000000000000001 /* Project object */;
}
"""

scheme_content = """<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1500"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "E00000000000000000000001"
               BuildableName = "RattApp.app"
               BlueprintName = "RattApp"
               ReferencedContainer = "container:Ratt.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES"
      shouldAutocreateTestPlan = "YES">
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "E00000000000000000000001"
            BuildableName = "RattApp.app"
            BlueprintName = "RattApp"
            ReferencedContainer = "container:Ratt.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "E00000000000000000000001"
            BuildableName = "RattApp.app"
            BlueprintName = "RattApp"
            ReferencedContainer = "container:Ratt.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
"""

with open(PBXPROJ_PATH, "w", encoding="utf-8") as f:
    f.write(content)

with open(SCHEME_PATH, "w", encoding="utf-8") as f:
    f.write(scheme_content)

print("Created", PBXPROJ_PATH)
print("Created", SCHEME_PATH)
