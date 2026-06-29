#include <adwaita.h>
#include <gdk/gdkkeysyms.h>
#include <gtk/gtk.h>

#include <stdlib.h>
#include <string.h>

#define APP_ID "io.github.kristopher.DestructiveConfirm"
#define EXIT_USAGE 2

static const char css[] =
    "window.destructive-confirm-compact {"
    "  background: transparent;"
    "}"
    ".destructive-confirm-card {"
    "  background: @window_bg_color;"
    "  border-radius: 14px;"
    "  padding: 20px;"
    "}"
    ".destructive-confirm-card button {"
    "  min-width: 260px;"
    "  min-height: 44px;"
    "  border-radius: 10px;"
    "}"
    "button.destructive-action {"
    "  background: #c01c28;"
    "  background-color: #c01c28;"
    "  background-image: none;"
    "  color: #ffffff;"
    "  text-shadow: none;"
    "}"
    "button.destructive-action:hover {"
    "  background: #e01b24;"
    "  background-color: #e01b24;"
    "  background-image: none;"
    "  color: #ffffff;"
    "}"
    "button.destructive-action:active {"
    "  background: #a51d2d;"
    "  background-color: #a51d2d;"
    "  background-image: none;"
    "  color: #ffffff;"
    "}"
    "button.destructive-action label {"
    "  color: #ffffff;"
    "  text-shadow: none;"
    "}";

typedef struct {
  char *title;
  char *text;
  char *confirm_label;
  char *cancel_label;
  int exit_status;
  GApplication *app;
} AppState;

static void finish(AppState *state, int exit_status);
static void install_css(void);
static gboolean has_text(const char *text);
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
  gtk_css_provider_load_from_string(provider, css);
  gtk_style_context_add_provider_for_display(
      display, GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_USER);
  g_object_unref(provider);
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

  adw_dialog_set_title(dialog, state->title);
  adw_dialog_present(dialog, NULL);
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
  gtk_widget_add_css_class(card, "destructive-confirm-card");

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
  gtk_window_set_child(GTK_WINDOW(window), card);
  gtk_window_set_default_widget(GTK_WINDOW(window), confirm_button);
  gtk_widget_grab_focus(confirm_button);

  key_controller = gtk_event_controller_key_new();
  g_signal_connect(key_controller, "key-pressed", G_CALLBACK(on_key_pressed),
                   state);
  gtk_widget_add_controller(window, key_controller);

  g_signal_connect(window, "close-request", G_CALLBACK(on_close_request),
                   state);

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
      {NULL}};

  context = g_option_context_new("- show a destructive confirmation dialog");
  g_option_context_add_main_entries(context, entries, NULL);

  if (!g_option_context_parse(context, argc, argv, &error)) {
    g_printerr("destructive-confirm: %s\n", error->message);
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

  app = adw_application_new(APP_ID, G_APPLICATION_NON_UNIQUE);
  g_signal_connect(app, "activate", G_CALLBACK(on_activate), &state);
  g_application_run(G_APPLICATION(app), app_argc, app_argv);

  app_state_clear(&state);
  return state.exit_status;
}
