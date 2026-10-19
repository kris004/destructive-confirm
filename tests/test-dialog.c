/* Exercise the real CLI dialog constructors and response handlers. */
#include <math.h>

int destructive_confirm_entrypoint(int argc, char **argv);
#define main destructive_confirm_entrypoint
#include "../src/destructive-confirm.c"
#undef main

static void
iterate_until(gboolean (*done)(gpointer), gpointer data) {
  gint64 deadline = g_get_monotonic_time() + G_TIME_SPAN_SECOND * 2;

  while (!done(data) && g_get_monotonic_time() < deadline) {
    g_main_context_iteration(NULL, FALSE);
    g_usleep(1000);
  }
  g_assert_true(done(data));
}

static gboolean
is_allocated(gpointer data) {
  return gtk_widget_get_width(GTK_WIDGET(data)) > 0;
}

static gboolean
is_finished(gpointer data) {
  return ((AppState *)data)->exit_status != 99;
}

static AdwApplication *
test_app(AppState *state) {
  static guint instance = 0;
  g_autofree char *id = g_strdup_printf(APP_ID ".Test%u", instance++);
  AdwApplication *app =
      adw_application_new(id, G_APPLICATION_NON_UNIQUE);
  g_autoptr(GError) error = NULL;
  g_application_register(G_APPLICATION(app), NULL, &error);
  g_assert_no_error(error);
  state->app = G_APPLICATION(app);
  state->title = "Dialog behavior test";
  state->confirm_label = "Delete";
  state->cancel_label = "Cancel";
  state->exit_status = 99;
  g_application_hold(state->app);
  return app;
}

static void
test_compact_responses(void) {
  for (guint action = 0; action < 5; action++) {
    AppState state = {0};
    g_autoptr(AdwApplication) app = test_app(&state);
    show_compact_window(&state);
    GtkWindow *window = gtk_application_get_windows(GTK_APPLICATION(app))->data;
    GtkWidget *confirm = gtk_window_get_default_widget(window);
    GtkWidget *cancel = gtk_widget_get_next_sibling(confirm);
    GtkWidget *fire = g_object_get_data(G_OBJECT(window), "fire-layer");
    iterate_until(is_allocated, confirm);

    g_assert_true(GTK_IS_BUTTON(confirm));
    g_assert_true(GTK_IS_LABEL(gtk_button_get_child(GTK_BUTTON(confirm))));
    g_assert_cmpstr(gtk_button_get_label(GTK_BUTTON(confirm)), ==, "Delete");
#if DC_ANIMATION_OVERLAY
    g_assert_nonnull(fire);
    g_assert_false(gtk_widget_get_can_target(fire));
    g_assert_false(gtk_widget_get_focusable(fire));
#else
    g_assert_null(fire);
#endif
    graphene_rect_t hit_bounds;
    g_assert_true(gtk_widget_compute_bounds(confirm, confirm, &hit_bounds));
    g_assert_false(gtk_widget_contains(confirm, hit_bounds.origin.x - 8, 10));
    g_assert_false(gtk_widget_contains(confirm, 10, hit_bounds.origin.y - 8));
    /* The original small ring deliberately used a wider decorative border. */
#if CONFIRM_ANIMATION != ANIMATION_FIRE_RING
    g_assert_cmpint(abs(gtk_widget_get_height(confirm) -
                         gtk_widget_get_height(cancel)), <=, 2);
#endif
    graphene_rect_t bounds;
    g_assert_true(gtk_widget_compute_bounds(cancel, confirm, &bounds));
    g_assert_cmpfloat(fabs(bounds.origin.y - hit_bounds.origin.y -
                           hit_bounds.size.height - 12), <=, 2);

    switch (action) {
    case 0:
      g_signal_emit_by_name(confirm, "clicked");
      break;
    case 1:
      g_assert_true(gtk_widget_activate(confirm)); /* Native Enter/Space action. */
      iterate_until(is_finished, &state);
      break;
    case 2:
      g_signal_emit_by_name(cancel, "clicked");
      break;
    case 3:
      g_assert_true(on_key_pressed(NULL, GDK_KEY_Escape, 0, 0, &state));
      break;
    case 4: {
      gboolean handled = FALSE;
      g_signal_emit_by_name(window, "close-request", &handled);
      g_assert_true(handled);
      break;
    }
    }
    g_assert_cmpint(state.exit_status, ==, action < 2 ? 0 : 1);
    gtk_window_destroy(window);
  }
}

static GtkWidget *
find_alert(GtkWidget *widget) {
  if (ADW_IS_ALERT_DIALOG(widget)) {
    return widget;
  }
  for (GtkWidget *child = gtk_widget_get_first_child(widget); child != NULL;
       child = gtk_widget_get_next_sibling(child)) {
    GtkWidget *alert = find_alert(child);
    if (alert != NULL) {
      return alert;
    }
  }
  return NULL;
}

static void
test_alert_responses(void) {
  for (guint action = 0; action < 2; action++) {
    AppState state = {0};
    g_autoptr(AdwApplication) app = test_app(&state);
    g_autofree char *title = g_strdup_printf("Alert response %u", action);
    state.title = title;
    state.text = "Delete this item?";
    show_alert_dialog(&state);
    GListModel *windows = gtk_window_get_toplevels();
    g_autoptr(GtkWindow) window = NULL;
    AdwAlertDialog *alert = NULL;
    for (guint i = 0; i < g_list_model_get_n_items(windows); i++) {
      GtkWindow *candidate = g_list_model_get_item(windows, i);
      if (!gtk_widget_get_visible(GTK_WIDGET(candidate))) {
        g_object_unref(candidate);
        continue;
      }
      GtkWidget *found = find_alert(GTK_WIDGET(candidate));
      if (found != NULL &&
          g_strcmp0(adw_dialog_get_title(ADW_DIALOG(found)), title) == 0) {
        window = candidate;
        alert = ADW_ALERT_DIALOG(found);
        break;
      }
      g_object_unref(candidate);
    }
    g_assert_nonnull(alert);
    GtkWidget *confirm = adw_dialog_get_default_widget(ADW_DIALOG(alert));
    iterate_until(is_allocated, confirm);
    g_assert_true(GTK_IS_BUTTON(confirm));
    g_assert_true(GTK_IS_LABEL(gtk_button_get_child(GTK_BUTTON(confirm))));
    g_assert_cmpstr(adw_alert_dialog_get_default_response(alert), ==, "confirm");
    g_assert_cmpstr(adw_alert_dialog_get_close_response(alert), ==, "cancel");
    g_assert_cmpstr(gtk_button_get_label(GTK_BUTTON(confirm)), ==, "Delete");
    g_test_message("Alert response %u", action);
    if (action == 0) {
      g_signal_emit_by_name(confirm, "clicked");
    } else {
      g_assert_true(adw_dialog_close(ADW_DIALOG(alert))); /* Escape action. */
    }
    iterate_until(is_finished, &state);
    g_assert_cmpint(state.exit_status, ==, action == 0 ? 0 : 1);
    if (gtk_widget_get_visible(GTK_WIDGET(window))) {
      gtk_window_destroy(window);
    }
  }
}

static void
test_motion_preferences(void) {
  AppState state = {0};
  g_autoptr(AdwApplication) app = test_app(&state);
  show_compact_window(&state);
  GtkWindow *window = gtk_application_get_windows(GTK_APPLICATION(app))->data;
  GtkSettings *settings = gtk_widget_get_settings(GTK_WIDGET(window));
  gboolean original = TRUE;
  gboolean high_contrast =
      adw_style_manager_get_high_contrast(adw_style_manager_get_default());

  g_object_get(settings, "gtk-enable-animations", &original, NULL);
  g_object_set(settings, "gtk-enable-animations", FALSE, NULL);
  g_assert_false(gtk_widget_has_css_class(
      GTK_WIDGET(window), "destructive-confirm-animated"));
#if GTK_CHECK_VERSION(4, 22, 0)
  GtkReducedMotion reduced;
  g_object_get(settings, "gtk-interface-reduced-motion", &reduced, NULL);
  g_object_set(settings, "gtk-interface-reduced-motion",
               GTK_REDUCED_MOTION_NO_PREFERENCE, NULL);
#endif
  g_object_set(settings, "gtk-enable-animations", TRUE, NULL);
  g_assert_cmpint(gtk_widget_has_css_class(
                     GTK_WIDGET(window), "destructive-confirm-animated"),
                 ==, !high_contrast && DC_ANIMATION_ENABLED);
#if GTK_CHECK_VERSION(4, 22, 0)
  g_object_set(settings, "gtk-interface-reduced-motion",
               GTK_REDUCED_MOTION_REDUCE, NULL);
  g_assert_false(gtk_widget_has_css_class(
      GTK_WIDGET(window), "destructive-confirm-animated"));
  g_object_set(settings, "gtk-interface-reduced-motion", reduced, NULL);
#endif
  g_object_set(settings, "gtk-enable-animations", original, NULL);
  on_close_request(window, &state);
  gtk_window_destroy(window);
}

int
main(int argc, char **argv) {
  g_test_init(&argc, &argv, NULL);
  adw_init();
  install_css();
  g_test_add_func("/dialog/compact-native-responses", test_compact_responses);
  g_test_add_func("/dialog/alert-native-responses", test_alert_responses);
  g_test_add_func("/dialog/motion-preferences", test_motion_preferences);
  return g_test_run();
}
