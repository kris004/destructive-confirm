/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Capture only the native demo widget, never the surrounding desktop.
 * Like the dialog tests, reuse the actual constructors and resource bundle.
 */
int destructive_confirm_entrypoint(int argc, char **argv);
#define main destructive_confirm_entrypoint
#include "../src/destructive-confirm.c"
#undef main

#include <glib/gstdio.h>

int
main(int argc, char **argv) {
  if (argc != 2) {
    g_printerr("Usage: capture-preview OUTPUT_DIRECTORY\n");
    return EXIT_USAGE;
  }
  if (g_mkdir_with_parents(argv[1], 0700) != 0) {
    g_printerr("Cannot create output directory\n");
    return EXIT_FAILURE;
  }
  for (guint frame = 0; frame < 180; frame++) {
    g_autofree char *path = g_strdup_printf("%s/%03u.png", argv[1], frame);
    if (g_file_test(path, G_FILE_TEST_EXISTS)) {
      g_printerr("Refusing to overwrite existing preview frames\n");
      return EXIT_FAILURE;
    }
  }

  adw_init();
  adw_style_manager_set_color_scheme(adw_style_manager_get_default(),
                                     ADW_COLOR_SCHEME_FORCE_DARK);
  install_css();
  g_autoptr(AdwApplication) app = adw_application_new(
      APP_ID ".Preview", G_APPLICATION_NON_UNIQUE);
  g_autoptr(GError) error = NULL;
  if (!g_application_register(G_APPLICATION(app), NULL, &error)) {
    g_printerr("Cannot register preview: %s\n", error->message);
    return EXIT_FAILURE;
  }
  AppState state = {
      .title = "Animation preview",
      .confirm_label = "Delete",
      .cancel_label = "Cancel",
      .exit_status = EXIT_FAILURE,
      .app = G_APPLICATION(app)};
  g_application_hold(state.app);
  show_compact_window(&state);
  GtkWindow *window = gtk_application_get_windows(GTK_APPLICATION(app))->data;
  gint64 deadline = g_get_monotonic_time() + 5 * G_TIME_SPAN_SECOND;
  while (gtk_widget_get_width(GTK_WIDGET(window)) == 0 &&
         g_get_monotonic_time() < deadline) {
    g_main_context_iteration(NULL, FALSE);
    g_usleep(1000);
  }
  int width = gtk_widget_get_width(GTK_WIDGET(window));
  int height = gtk_widget_get_height(GTK_WIDGET(window));
  if (width <= 0 || height <= 0) {
    g_printerr("Preview was not allocated\n");
    gtk_window_destroy(window);
    return EXIT_FAILURE;
  }

  g_autoptr(GdkPaintable) paintable =
      gtk_widget_paintable_new(GTK_WIDGET(window));
  GskRenderer *renderer = gtk_native_get_renderer(GTK_NATIVE(window));
  graphene_rect_t viewport = GRAPHENE_RECT_INIT(0, 0, width, height);
  gint64 started = g_get_monotonic_time();
  for (guint frame = 0; frame < 180; frame++) {
    gint64 target = started + frame * G_TIME_SPAN_SECOND / 30;
    while (g_get_monotonic_time() < target) {
      g_main_context_iteration(NULL, FALSE);
      g_usleep(1000);
    }
    g_main_context_iteration(NULL, FALSE);
    g_autoptr(GtkSnapshot) snapshot = gtk_snapshot_new();
    gdk_paintable_snapshot(paintable, GDK_SNAPSHOT(snapshot), width, height);
    g_autoptr(GskRenderNode) node = gtk_snapshot_to_node(snapshot);
    if (node == NULL) {
      g_printerr("Preview frame is empty\n");
      gtk_window_destroy(window);
      return EXIT_FAILURE;
    }
    g_autoptr(GdkTexture) texture =
        gsk_renderer_render_texture(renderer, node, &viewport);
    g_autofree char *path =
        g_strdup_printf("%s/%03u.png", argv[1], frame);
    if (!gdk_texture_save_to_png(texture, path)) {
      g_printerr("Cannot save preview frame\n");
      gtk_window_destroy(window);
      return EXIT_FAILURE;
    }
  }
  gtk_window_destroy(window);
  g_application_release(state.app);
  return EXIT_SUCCESS;
}
