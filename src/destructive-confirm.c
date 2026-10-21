/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <adwaita.h>
#include <gdk/gdkkeysyms.h>
#include <gtk/gtk.h>

#include "animation-config.h"
#if DC_ANIMATION_OVERLAY
#include "fire-overlay.h"
#endif

#include <stdlib.h>
#include <string.h>

#define APP_ID "io.github.kristopher.DestructiveConfirm"
#define EXIT_USAGE 2

typedef struct {
  char *title;
  char *text;
  char *confirm_label;
  char *cancel_label;
  gboolean show_version;
  gboolean finished;
  guint alert_close_idle;
  int exit_status;
  GApplication *app;
} AppState;

static void finish(AppState *state, int exit_status);
static void install_css(void);
static void update_effect_preferences(GObject *object, GParamSpec *pspec,
                                      gpointer user_data);
static void watch_effect_preferences(GtkWidget *widget);
static gboolean has_text(const char *text);
static void on_alert_root_changed(GObject *object, GParamSpec *pspec,
                                  gpointer user_data);
static gboolean on_alert_window_close(GtkWindow *window, gpointer user_data);
static gboolean finish_alert_close(gpointer user_data);
static void show_alert_dialog(AppState *state);
static void show_compact_window(AppState *state);
static void on_response(AdwAlertDialog *dialog, const char *response,
                        gpointer user_data);
static void on_confirm_clicked(GtkButton *button, gpointer user_data);
static void on_cancel_clicked(GtkButton *button, gpointer user_data);
static gboolean on_close_request(GtkWindow *window, gpointer user_data);
static gboolean on_key_pressed(GtkEventControllerKey *controller, guint keyval,
                               guint keycode, GdkModifierType state,
                               gpointer user_data);
static void on_activate(GApplication *app, gpointer user_data);
static gboolean parse_options(int *argc, char ***argv, AppState *state);
static void app_state_clear(AppState *state);

static void
finish(AppState *state, int exit_status) {
  if (state->finished) {
    return;
  }
  state->finished = TRUE;
  if (state->alert_close_idle != 0) {
    g_source_remove(state->alert_close_idle);
    state->alert_close_idle = 0;
  }
  state->exit_status = exit_status;
  g_application_release(state->app);
  g_application_quit(state->app);
}

static void
install_css(void) {
  GdkDisplay *display = gdk_display_get_default();

  if (display == NULL) {
    return;
  }

  GtkCssProvider *provider = gtk_css_provider_new();
  gtk_css_provider_load_from_resource(
      provider, "/io/github/kristopher/DestructiveConfirm/style.css");
  gtk_style_context_add_provider_for_display(
      display, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_USER);
  g_object_unref(provider);
}

static void
update_effect_preferences(GObject *object, GParamSpec *pspec,
                          gpointer user_data) {
  GtkWidget *widget = GTK_WIDGET(user_data);
  GtkSettings *settings = gtk_widget_get_settings(widget);
  AdwStyleManager *style_manager =
      adw_style_manager_get_for_display(gtk_widget_get_display(widget));
  gboolean animations = TRUE;
  gboolean high_contrast = adw_style_manager_get_high_contrast(style_manager);

  (void)object;
  (void)pspec;

  g_object_get(settings, "gtk-enable-animations", &animations, NULL);
  animations = animations && DC_ANIMATION_ENABLED;
#if GTK_CHECK_VERSION(4, 22, 0)
  GtkReducedMotion reduced_motion = GTK_REDUCED_MOTION_NO_PREFERENCE;

  g_object_get(settings, "gtk-interface-reduced-motion", &reduced_motion, NULL);
  animations = animations && reduced_motion == GTK_REDUCED_MOTION_NO_PREFERENCE;
#endif

  if (animations && !high_contrast) {
    gtk_widget_add_css_class(widget, "destructive-confirm-animated");
  } else {
    gtk_widget_remove_css_class(widget, "destructive-confirm-animated");
  }

  if (high_contrast) {
    gtk_widget_add_css_class(widget, "destructive-confirm-high-contrast");
  } else {
    gtk_widget_remove_css_class(widget, "destructive-confirm-high-contrast");
  }
#if DC_ANIMATION_OVERLAY
  fire_overlay_set_preferences(widget, animations && !high_contrast,
                                !high_contrast);
#endif
}

static void
watch_effect_preferences(GtkWidget *widget) {
  GtkSettings *settings = gtk_widget_get_settings(widget);
  AdwStyleManager *style_manager =
      adw_style_manager_get_for_display(gtk_widget_get_display(widget));

  update_effect_preferences(NULL, NULL, widget);
  g_signal_connect_object(settings, "notify::gtk-enable-animations",
                          G_CALLBACK(update_effect_preferences), widget, 0);
#if GTK_CHECK_VERSION(4, 22, 0)
  g_signal_connect_object(settings, "notify::gtk-interface-reduced-motion",
                          G_CALLBACK(update_effect_preferences), widget, 0);
#endif
  g_signal_connect_object(style_manager, "notify::high-contrast",
                          G_CALLBACK(update_effect_preferences), widget, 0);
}

static gboolean
has_text(const char *text) {
  if (text == NULL || text[0] == '\0') {
    return FALSE;
  }

  return TRUE;
}

static void
on_response(AdwAlertDialog *dialog, const char *response, gpointer user_data) {
  AppState *state = user_data;

  (void)dialog;

  finish(state,
         g_strcmp0(response, "confirm") == 0 ? EXIT_SUCCESS : EXIT_FAILURE);
}

static void
on_alert_root_changed(GObject *object, GParamSpec *pspec, gpointer user_data) {
  GtkRoot *root = gtk_widget_get_root(GTK_WIDGET(object));
  AppState *state = user_data;

  (void)pspec;

  /* Associate the standalone window before GTK realizes its native surface. */
  if (GTK_IS_WINDOW(root)) {
    gtk_window_set_application(GTK_WINDOW(root), GTK_APPLICATION(state->app));
    g_signal_connect(root, "close-request",
                     G_CALLBACK(on_alert_window_close), state);
  }
}

static gboolean
finish_alert_close(gpointer user_data) {
  AppState *state = user_data;

  state->alert_close_idle = 0;
  finish(state, EXIT_FAILURE);
  return G_SOURCE_REMOVE;
}

static gboolean
on_alert_window_close(GtkWindow *window, gpointer user_data) {
  AppState *state = user_data;

  (void)window;
  /* libadwaita 1.5 omits the closed/response signal for standalone windows.
   * Defer cancellation: a native response button closes the window before
   * emitting its response, and that response must win over this fallback.
   */
  if (!state->finished && state->alert_close_idle == 0) {
    state->alert_close_idle = g_idle_add(finish_alert_close, state);
  }
  return GDK_EVENT_PROPAGATE;
}

static void
show_alert_dialog(AppState *state) {
  AdwDialog *dialog = NULL;
  AdwAlertDialog *alert = NULL;

  dialog = adw_alert_dialog_new(state->text, NULL);
  alert = ADW_ALERT_DIALOG(dialog);

  adw_alert_dialog_add_response(alert, "cancel", state->cancel_label);
  adw_alert_dialog_add_response(alert, "confirm", state->confirm_label);
  adw_alert_dialog_set_close_response(alert, "cancel");
  adw_alert_dialog_set_default_response(alert, "confirm");
  adw_alert_dialog_set_response_appearance(alert, "confirm",
                                           ADW_RESPONSE_DESTRUCTIVE);
  g_signal_connect(alert, "response", G_CALLBACK(on_response), state);

#if DC_ANIMATION_OVERLAY
  /* Wrap the content once; response buttons and their handlers stay intact. */
  GtkWidget *content = adw_dialog_get_child(dialog);
  GtkWidget *button = adw_dialog_get_default_widget(dialog);
  g_object_ref(content);
  adw_dialog_set_child(dialog, NULL);
  GtkWidget *overlay = fire_overlay_new(content, button, GTK_WIDGET(dialog));
  g_object_unref(content);
  gtk_widget_add_css_class(overlay, "destructive-confirm-alert-card");
  gtk_widget_add_css_class(overlay, "destructive-confirm-fire-space");
  gtk_widget_add_css_class(GTK_WIDGET(dialog), "destructive-confirm-alert");
  adw_dialog_set_child(dialog, overlay);
#endif
  adw_dialog_set_title(dialog, state->title);
  watch_effect_preferences(GTK_WIDGET(dialog));
  g_signal_connect(dialog, "notify::root",
                   G_CALLBACK(on_alert_root_changed), state);
  adw_dialog_present(dialog, NULL);
#if DC_ANIMATION_OVERLAY
  GtkRoot *root = gtk_widget_get_root(GTK_WIDGET(dialog));
  if (root != NULL) {
    gtk_widget_add_css_class(GTK_WIDGET(root), "destructive-confirm-shell");
  }
#endif
}

static void
show_compact_window(AppState *state) {
  GtkWidget *window = NULL;
  GtkWidget *card = NULL;
  GtkWidget *confirm_button = NULL;
  GtkWidget *cancel_button = NULL;
  GtkEventController *key_controller = NULL;

  window = gtk_application_window_new(GTK_APPLICATION(state->app));
  gtk_window_set_title(GTK_WINDOW(window), state->title);
  gtk_window_set_decorated(GTK_WINDOW(window), FALSE);
  gtk_window_set_resizable(GTK_WINDOW(window), FALSE);
  gtk_widget_add_css_class(window, "destructive-confirm-compact");

  card = gtk_box_new(GTK_ORIENTATION_VERTICAL, 12);
#if !DC_ANIMATION_OVERLAY
  gtk_widget_add_css_class(card, "destructive-confirm-card");
#endif

  confirm_button = gtk_button_new_with_label(state->confirm_label);
  gtk_widget_add_css_class(confirm_button, "destructive-action");
  gtk_widget_add_css_class(confirm_button, "text-button");
  gtk_widget_set_receives_default(confirm_button, TRUE);
  g_signal_connect(confirm_button, "clicked", G_CALLBACK(on_confirm_clicked),
                   state);

  cancel_button = gtk_button_new_with_label(state->cancel_label);
  gtk_widget_add_css_class(cancel_button, "text-button");
  g_signal_connect(cancel_button, "clicked", G_CALLBACK(on_cancel_clicked),
                   state);

  gtk_box_append(GTK_BOX(card), confirm_button);
  gtk_box_append(GTK_BOX(card), cancel_button);
#if DC_ANIMATION_OVERLAY
  GtkWidget *overlay = fire_overlay_new(card, confirm_button, window);
  gtk_widget_add_css_class(overlay, "destructive-confirm-card");
  gtk_widget_add_css_class(overlay, "destructive-confirm-fire-space");
  gtk_window_set_child(GTK_WINDOW(window), overlay);
#else
  gtk_window_set_child(GTK_WINDOW(window), card);
#endif
  gtk_window_set_default_widget(GTK_WINDOW(window), confirm_button);
  gtk_widget_grab_focus(confirm_button);

  key_controller = gtk_event_controller_key_new();
  g_signal_connect(key_controller, "key-pressed", G_CALLBACK(on_key_pressed),
                   state);
  gtk_widget_add_controller(window, key_controller);

  g_signal_connect(window, "close-request", G_CALLBACK(on_close_request),
                   state);

  watch_effect_preferences(window);
  gtk_window_present(GTK_WINDOW(window));
}

static void
on_confirm_clicked(GtkButton *button, gpointer user_data) {
  AppState *state = user_data;

  (void)button;

  finish(state, EXIT_SUCCESS);
}

static void
on_cancel_clicked(GtkButton *button, gpointer user_data) {
  AppState *state = user_data;

  (void)button;

  finish(state, EXIT_FAILURE);
}

static gboolean
on_close_request(GtkWindow *window, gpointer user_data) {
  AppState *state = user_data;

  (void)window;

  finish(state, EXIT_FAILURE);
  return TRUE;
}

static gboolean
on_key_pressed(GtkEventControllerKey *controller, guint keyval, guint keycode,
               GdkModifierType key_state, gpointer user_data) {
  AppState *state = user_data;

  (void)controller;
  (void)keycode;
  (void)key_state;

  if (keyval == GDK_KEY_Escape) {
    finish(state, EXIT_FAILURE);
    return TRUE;
  }

  return FALSE;
}

static void
on_activate(GApplication *app, gpointer user_data) {
  AppState *state = user_data;

  state->app = app;
  g_application_hold(app);
  install_css();

  if (has_text(state->text)) {
    show_alert_dialog(state);
    return;
  }

  show_compact_window(state);
}

static gboolean
parse_options(int *argc, char ***argv, AppState *state) {
  g_autoptr(GError) error = NULL;
  g_autoptr(GOptionContext) context = NULL;
  GOptionEntry entries[] = {
      {"title", 0, 0, G_OPTION_ARG_STRING, &state->title,
       "Dialog title", "TITLE"},
      {"text", 0, 0, G_OPTION_ARG_STRING, &state->text,
       "Confirmation text", "TEXT"},
      {"confirm-label", 0, 0, G_OPTION_ARG_STRING, &state->confirm_label,
       "Confirm button label", "LABEL"},
      {"cancel-label", 0, 0, G_OPTION_ARG_STRING, &state->cancel_label,
       "Cancel button label", "LABEL"},
      {"version", 0, 0, G_OPTION_ARG_NONE, &state->show_version,
       "Print version without opening a dialog", NULL},
      {NULL}};

  context = g_option_context_new("- show a destructive confirmation dialog");
  g_option_context_add_main_entries(context, entries, NULL);

  if (!g_option_context_parse(context, argc, argv, &error)) {
    g_printerr("destructive-confirm: %s\n", error->message);
    return FALSE;
  }

  if (*argc > 1) {
    g_printerr("destructive-confirm: unexpected argument: %s\n", (*argv)[1]);
    return FALSE;
  }

  if (state->title == NULL) {
    state->title = g_strdup("Confirm");
  }
  if (state->confirm_label == NULL) {
    state->confirm_label = g_strdup("OK");
  }
  if (state->cancel_label == NULL) {
    state->cancel_label = g_strdup("Cancel");
  }

  return TRUE;
}

static void
app_state_clear(AppState *state) {
  if (state->alert_close_idle != 0) {
    g_source_remove(state->alert_close_idle);
    state->alert_close_idle = 0;
  }
  g_free(state->title);
  g_free(state->text);
  g_free(state->confirm_label);
  g_free(state->cancel_label);
}

int
main(int argc, char **argv) {
  AppState state = {.exit_status = EXIT_FAILURE};
  g_autoptr(AdwApplication) app = NULL;
  char *app_argv[] = {argv[0], NULL};
  int app_argc = 1;

  if (!parse_options(&argc, &argv, &state)) {
    app_state_clear(&state);
    return EXIT_USAGE;
  }

  if (state.show_version) {
    g_print("destructive-confirm %s\n", DC_VERSION);
    app_state_clear(&state);
    return EXIT_SUCCESS;
  }

  app = adw_application_new(APP_ID, G_APPLICATION_NON_UNIQUE);
  g_signal_connect(app, "activate", G_CALLBACK(on_activate), &state);
  g_application_run(G_APPLICATION(app), app_argc, app_argv);

  app_state_clear(&state);
  return state.exit_status;
}
