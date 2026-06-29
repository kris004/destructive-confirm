#include <adwaita.h>
#include <gtk/gtk.h>

#include <stdlib.h>
#include <string.h>

#define APP_ID "io.github.kristopher.PowerConfirm"
#define EXIT_USAGE 2

static const char css[] =
    "button.destructive-action,"
    "button.destructive-action label {"
    "  color: #ffffff;"
    "}";

typedef struct {
  char *title;
  char *text;
  char *confirm_label;
  char *cancel_label;
  int exit_status;
  GApplication *app;
} AppState;

static void install_css(void);
static void on_response(AdwAlertDialog *dialog, const char *response,
                        gpointer user_data);
static void on_activate(GApplication *app, gpointer user_data);
static gboolean parse_options(int *argc, char ***argv, AppState *state);
static void app_state_clear(AppState *state);

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

static void
on_response(AdwAlertDialog *dialog, const char *response, gpointer user_data) {
  AppState *state = user_data;

  (void)dialog;

  state->exit_status = g_strcmp0(response, "confirm") == 0 ? EXIT_SUCCESS
                                                            : EXIT_FAILURE;
  g_application_release(state->app);
  g_application_quit(state->app);
}

static void
on_activate(GApplication *app, gpointer user_data) {
  AppState *state = user_data;
  AdwDialog *dialog = NULL;
  AdwAlertDialog *alert = NULL;

  state->app = app;
  g_application_hold(app);
  install_css();

  dialog = adw_alert_dialog_new(state->text, "");
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
    g_printerr("power-confirm: %s\n", error->message);
    return FALSE;
  }

  if (state->text == NULL || state->text[0] == '\0') {
    g_printerr("power-confirm: --text is required\n");
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

  app = adw_application_new(APP_ID, G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect(app, "activate", G_CALLBACK(on_activate), &state);
  g_application_run(G_APPLICATION(app), app_argc, app_argv);

  app_state_clear(&state);
  return state.exit_status;
}
