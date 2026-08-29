from pathlib import Path
import re

root = Path('j2me')

# App identity / package.
p = root / 'app/build.gradle'
s = p.read_text()
s = s.replace('applicationId "ru.playsoftware.j2meloader"', 'applicationId "com.caio.toystory3.fold"', 1)
s = s.replace("resValue 'string', 'app_name', rootProject.name", "resValue 'string', 'app_name', 'Toy Story 3'", 1)
s = s.replace('versionName "1.8.2"', 'versionName "1.0.51-fold4"', 1)
p.write_text(s)

# MainActivity: feed the bundled JAR to the installer automatically.
p = root / 'app/src/main/java/ru/playsoftware/j2meloader/MainActivity.java'
s = p.read_text()
s = s.replace(
    'import java.io.File;\nimport java.util.Map;',
    'import java.io.File;\nimport java.io.FileOutputStream;\nimport java.io.InputStream;\nimport java.io.IOException;\nimport java.util.Map;'
)
s = s.replace(
    '\t\tsetContentView(R.layout.activity_main);\n',
    '\t\tsetContentView(R.layout.activity_main);\n\t\tFileUtils.initWorkDir(new File(Config.getEmulatorDir()));\n',
    1
)
old = "\t\t\tif ((intent.getFlags() & Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY) == 0) {\n\t\t\t\turi = intent.getData();\n\t\t\t}\n\t\t\tAppsListFragment fragment = AppsListFragment.newInstance(uri);"
new = "\t\t\tif ((intent.getFlags() & Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY) == 0) {\n\t\t\t\turi = intent.getData();\n\t\t\t}\n\t\t\tif (uri == null) {\n\t\t\t\turi = getBundledGameUri();\n\t\t\t}\n\t\t\tAppsListFragment fragment = AppsListFragment.newInstance(uri);"
if old not in s:
    raise SystemExit('MainActivity intent block not found')
s = s.replace(old, new, 1)

warning = "\t\tboolean warningShown = preferences.getBoolean(PREF_STORAGE_WARNING_SHOWN, false);\n\t\tif (!FileUtils.isExternalStorageLegacy() && !warningShown) {\n\t\t\tshowScopedStorageDialog();\n\t\t\tpreferences.edit().putBoolean(PREF_STORAGE_WARNING_SHOWN, true).apply();\n\t\t}"
s = s.replace(warning, '\t\tpreferences.edit().putBoolean(PREF_STORAGE_WARNING_SHOWN, true).apply();', 1)

helper = """
\tprivate Uri getBundledGameUri() {
\t\tFile game = new File(getFilesDir(), \"ToyStory3.jar\");
\t\tif (!game.exists() || game.length() == 0) {
\t\t\ttry (InputStream in = getAssets().open(\"toystory3.jar\");
\t\t\t\t FileOutputStream out = new FileOutputStream(game)) {
\t\t\t\tbyte[] buffer = new byte[16384];
\t\t\t\tint read;
\t\t\t\twhile ((read = in.read(buffer)) != -1) {
\t\t\t\t\tout.write(buffer, 0, read);
\t\t\t\t}
\t\t\t} catch (IOException e) {
\t\t\t\tthrow new RuntimeException(\"Unable to prepare bundled Toy Story 3 MIDlet\", e);
\t\t\t}
\t\t}
\t\treturn Uri.fromFile(game);
\t}

"""
marker = '\t@Override\n\tprotected void onNewIntent(Intent intent) {'
if marker not in s:
    raise SystemExit('MainActivity onNewIntent marker not found')
s = s.replace(marker, helper + marker, 1)
p.write_text(s)

# Installer: zero-click installation and launch.
p = root / 'app/src/main/java/ru/woesss/j2me/installer/InstallerDialog.java'
s = p.read_text()
pat = re.compile(r'\t\tif \(status == AppInstaller\.STATUS_SUCCESS\) \{.*?\n\t\t\}\n\t\tDescriptor nd', re.S)
repl = "\t\tif (status == AppInstaller.STATUS_SUCCESS) {\n\t\t\tAppItem app = installer.getExistsApp();\n\t\t\tConfig.startApp(requireActivity(), app.getTitle(), app.getPathExt(), false);\n\t\t\trequireActivity().finish();\n\t\t\tdismiss();\n\t\t\treturn;\n\t\t}\n\t\tDescriptor nd"
s, n = pat.subn(lambda m: repl, s, count=1)
if n != 1:
    raise SystemExit('Installer success block not patched')

pat = re.compile(r'\t\t\tcase AppInstaller\.STATUS_EQUAL:.*?\n\t\t\t\tbreak;', re.S)
repl = "\t\t\tcase AppInstaller.STATUS_EQUAL:\n\t\t\t\tAppItem existingApp = installer.getExistsApp();\n\t\t\t\tinstaller.clearCache();\n\t\t\t\tinstaller.deleteTemp();\n\t\t\t\tConfig.startApp(requireActivity(), existingApp.getTitle(), existingApp.getPathExt(), false);\n\t\t\t\trequireActivity().finish();\n\t\t\t\tdismiss();\n\t\t\t\treturn;"
s, n = pat.subn(lambda m: repl, s, count=1)
if n != 1:
    raise SystemExit('Installer equal block not patched')
p.write_text(s)

# Config.startApp: create a tuned Fold4 profile automatically.
p = root / 'app/src/main/java/ru/playsoftware/j2meloader/config/Config.java'
s = p.read_text()
pat = re.compile(
    r'\tpublic static void startApp\(Context context, String name, String path, boolean showSettings, String arguments\) \{.*?\n\t\}\n\n\tprivate static void initDirs',
    re.S
)
repl = """\tpublic static void startApp(Context context, String name, String path, boolean showSettings, String arguments) {
\t\tFile appDir = new File(path);
\t\tString workDir = appDir.getParentFile().getParent();
\t\tFile configDir = new File(workDir + Config.MIDLET_CONFIGS_DIR + appDir.getName());
\t\tFile configFile = new File(configDir, Config.MIDLET_CONFIG_FILE);

\t\tif (showSettings) {
\t\t\tIntent intent = new Intent(ACTION_EDIT, Uri.parse(path), context, ConfigActivity.class);
\t\t\tintent.putExtra(KEY_MIDLET_NAME, name);
\t\t\tintent.putExtra(KEY_START_ARGUMENTS, arguments);
\t\t\tcontext.startActivity(intent);
\t\t\treturn;
\t\t}

\t\tif (!configFile.exists()) {
\t\t\tconfigDir.mkdirs();
\t\t\tProfileModel profile = new ProfileModel(configDir);
\t\t\tprofile.screenWidth = 240;
\t\t\tprofile.screenHeight = 320;
\t\t\tprofile.orientation = 2; // portrait
\t\t\tprofile.screenScaleType = 1; // fit
\t\t\tprofile.screenGravity = 2; // center
\t\t\tprofile.screenScaleRatio = 100;
\t\t\tprofile.screenFilter = true;
\t\t\tprofile.graphicsMode = 1; // OpenGL ES
\t\t\tprofile.forceFullscreen = true;
\t\t\tprofile.fontAA = true;
\t\t\tprofile.showKeyboard = true;
\t\t\tprofile.touchInput = true;
\t\t\tprofile.vkAlpha = 104;
\t\t\tProfilesManager.saveConfig(profile);
\t\t}

\t\tIntent intent = new Intent(Intent.ACTION_DEFAULT, Uri.parse(path), context, MicroActivity.class);
\t\tintent.putExtra(KEY_MIDLET_NAME, name);
\t\tintent.putExtra(KEY_START_ARGUMENTS, arguments);
\t\tcontext.startActivity(intent);
\t}

\tprivate static void initDirs"""
s, n = pat.subn(lambda m: repl, s, count=1)
if n != 1:
    raise SystemExit('Config.startApp not patched')
p.write_text(s)

# Default profile consistency.
p = root / 'app/src/main/java/ru/playsoftware/j2meloader/config/ProfileModel.java'
s = p.read_text()
s = s.replace('\t\tscreenGravity = 1;', '\t\tscreenGravity = 2;', 1)
s = s.replace('\t\tgraphicsMode = 1;', '\t\tgraphicsMode = 1;\n\t\tscreenFilter = true;\n\t\tforceFullscreen = true;\n\t\torientation = 2;', 1)
s = s.replace('\t\tvkAlpha = 64;', '\t\tvkAlpha = 104;', 1)
p.write_text(s)

# Use original MIDlet icon for Android launcher.
p = root / 'app/src/main/AndroidManifest.xml'
s = p.read_text()
s = s.replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@drawable/toystory_icon"', 1)
s = s.replace('android:roundIcon="@mipmap/ic_launcher"', 'android:roundIcon="@drawable/toystory_icon"', 1)
p.write_text(s)

print('Patch completed successfully.')
