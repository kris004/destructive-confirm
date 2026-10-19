#include "fire-overlay.h"
#include "../data/fire-art.h"

#include <math.h>

#define TYPE_FIRE_LAYER (fire_layer_get_type())
G_DECLARE_FINAL_TYPE(FireLayer, fire_layer, DC, FIRE_LAYER, GtkWidget)

typedef struct {
  GdkTexture *texture;
  guint frame;
  guint64 used;
} CachedFrame;

struct _FireLayer {
  GtkWidget parent_instance;
  GtkWidget *button; /* Weak: never keep a response button alive. */
  CachedFrame cache[4];
  guint64 serial;
  guint tick_id;
  gint64 started;
  double elapsed;
  gboolean animated;
  gboolean visible;
  gboolean input_set;
  cairo_rectangle_int_t input_rect;
};

G_DEFINE_TYPE(FireLayer, fire_layer, GTK_TYPE_WIDGET)

static void
update_input_region(FireLayer *self) {
  GtkWidget *card = gtk_widget_get_parent(GTK_WIDGET(self));
  GtkNative *native = gtk_widget_get_native(GTK_WIDGET(self));
  graphene_rect_t bounds;

  if (card == NULL || native == NULL ||
      !gtk_widget_compute_bounds(card, GTK_WIDGET(native), &bounds)) {
    return;
  }
  double surface_x, surface_y;
  gtk_native_get_surface_transform(native, &surface_x, &surface_y);
  /* Match GtkWindow's input-shape calculation, including CSD shadows. */
  double x = bounds.origin.x + surface_x;
  double y = bounds.origin.y + surface_y;
  cairo_rectangle_int_t rect = {
      (int)floor(x), (int)floor(y),
      (int)ceil(x + bounds.size.width) - (int)floor(x),
      (int)ceil(y + bounds.size.height) - (int)floor(y)};
  if (self->input_set && self->input_rect.x == rect.x &&
      self->input_rect.y == rect.y && self->input_rect.width == rect.width &&
      self->input_rect.height == rect.height) {
    return;
  }
  GdkSurface *surface = gtk_native_get_surface(native);
  if (surface != NULL) {
    cairo_region_t *region = cairo_region_create_rectangle(&rect);
    gdk_surface_set_input_region(surface, region);
    cairo_region_destroy(region);
    self->input_rect = rect;
    self->input_set = TRUE;
  }
}

static GdkTexture *
frame_texture(FireLayer *self, guint frame) {
  guint oldest = 0;

  for (guint i = 0; i < G_N_ELEMENTS(self->cache); i++) {
    if (self->cache[i].texture != NULL && self->cache[i].frame == frame) {
      self->cache[i].used = ++self->serial;
      return self->cache[i].texture;
    }
    if (self->cache[i].used < self->cache[oldest].used) {
      oldest = i;
    }
  }

  CachedFrame *entry = &self->cache[oldest];
  g_autofree char *path = g_strdup_printf(
      "/io/github/kristopher/DestructiveConfirm/fire/%03u.png", frame);

  g_clear_object(&entry->texture);
  entry->texture = gdk_texture_new_from_resource(path);
  entry->frame = frame;
  entry->used = ++self->serial;
  return entry->texture;
}

static void
snapshot_patch(GtkSnapshot *snapshot, GdkTexture *texture,
                float sx, float sy, float sw, float sh,
                float dx, float dy, float dw, float dh) {
  if (dw <= 0 || dh <= 0) {
    return;
  }

  graphene_rect_t clip = GRAPHENE_RECT_INIT(dx, dy, dw, dh);
  graphene_point_t offset = GRAPHENE_POINT_INIT(dx - sx * dw / sw,
                                                dy - sy * dh / sh);
  graphene_rect_t image = GRAPHENE_RECT_INIT(0, 0, FIRE_FRAME_WIDTH,
                                             FIRE_FRAME_HEIGHT);

  gtk_snapshot_push_clip(snapshot, &clip);
  gtk_snapshot_save(snapshot);
  gtk_snapshot_translate(snapshot, &offset);
  gtk_snapshot_scale(snapshot, dw / sw, dh / sh);
  gtk_snapshot_append_texture(snapshot, texture, &image);
  gtk_snapshot_restore(snapshot);
  gtk_snapshot_pop(snapshot);
}

static void
snapshot_frame(FireLayer *self, GtkSnapshot *snapshot,
                const graphene_rect_t *button, guint frame) {
  GdkTexture *texture = frame_texture(self, frame);
  const float sx[] = {0, FIRE_SLICE_X, FIRE_FRAME_WIDTH - FIRE_SLICE_X,
                       FIRE_FRAME_WIDTH};
  const float sy[] = {0, FIRE_SLICE_Y, FIRE_FRAME_HEIGHT - FIRE_SLICE_Y,
                       FIRE_FRAME_HEIGHT};
  const float dx[] = {button->origin.x - FIRE_PADDING_X,
                       button->origin.x + FIRE_CORNER,
                       button->origin.x + button->size.width - FIRE_CORNER,
                       button->origin.x + button->size.width + FIRE_PADDING_X};
  const float dy[] = {button->origin.y - FIRE_PADDING_Y,
                       button->origin.y + FIRE_CORNER,
                       button->origin.y + button->size.height - FIRE_CORNER,
                       button->origin.y + button->size.height + FIRE_PADDING_Y};

  for (guint y = 0; y < 3; y++) {
    for (guint x = 0; x < 3; x++) {
      if (x == 1 && y == 1) {
        continue; /* The label area is never painted. */
      }
      snapshot_patch(snapshot, texture, sx[x], sy[y], sx[x + 1] - sx[x],
                      sy[y + 1] - sy[y], dx[x], dy[y], dx[x + 1] - dx[x],
                      dy[y + 1] - dy[y]);
    }
  }
}

static void
fire_layer_snapshot(GtkWidget *widget, GtkSnapshot *snapshot) {
  FireLayer *self = DC_FIRE_LAYER(widget);
  graphene_rect_t button;

  /* Transparent flame overhang must not intercept clicks on other apps. */
  update_input_region(self);
  if (!self->visible || self->button == NULL ||
      !gtk_widget_compute_bounds(self->button, widget, &button)) {
    return;
  }

  double position = FIRE_INTRO_FRAMES;
  if (self->animated) {
    position = self->elapsed * FIRE_FPS;
    if (position >= FIRE_INTRO_FRAMES) {
      position = FIRE_INTRO_FRAMES +
                 fmod(position - FIRE_INTRO_FRAMES, FIRE_LOOP_FRAMES);
    }
  }
  guint first = (guint)floor(position);
  guint second = first + 1;
  if (second == FIRE_INTRO_FRAMES + FIRE_LOOP_FRAMES) {
    second = FIRE_INTRO_FRAMES;
  }
  double blend = position - first;

  if (!self->animated || blend < 0.001) {
    snapshot_frame(self, snapshot, &button, first);
    return;
  }
  /* Interpolate at the display's frame rate, not the asset's 30 fps. */
  gtk_snapshot_push_cross_fade(snapshot, blend);
  snapshot_frame(self, snapshot, &button, first);
  gtk_snapshot_pop(snapshot);
  snapshot_frame(self, snapshot, &button, second);
  gtk_snapshot_pop(snapshot);
}

static gboolean
fire_layer_tick(GtkWidget *widget, GdkFrameClock *clock, gpointer user_data) {
  FireLayer *self = DC_FIRE_LAYER(widget);
  gint64 now = gdk_frame_clock_get_frame_time(clock);

  (void)user_data;
  if (self->started == 0) {
    self->started = now;
  }
  self->elapsed = (now - self->started) / 1000000.0;
  gtk_widget_queue_draw(widget);
  return G_SOURCE_CONTINUE;
}

static void
fire_layer_dispose(GObject *object) {
  FireLayer *self = DC_FIRE_LAYER(object);

  if (self->tick_id != 0) {
    gtk_widget_remove_tick_callback(GTK_WIDGET(self), self->tick_id);
    self->tick_id = 0;
  }
  if (self->button != NULL) {
    g_object_remove_weak_pointer(G_OBJECT(self->button),
                                 (gpointer *)&self->button);
    self->button = NULL;
  }
  for (guint i = 0; i < G_N_ELEMENTS(self->cache); i++) {
    g_clear_object(&self->cache[i].texture);
  }
  G_OBJECT_CLASS(fire_layer_parent_class)->dispose(object);
}

static void
fire_layer_class_init(FireLayerClass *klass) {
  G_OBJECT_CLASS(klass)->dispose = fire_layer_dispose;
  GTK_WIDGET_CLASS(klass)->snapshot = fire_layer_snapshot;
  gtk_widget_class_set_accessible_role(GTK_WIDGET_CLASS(klass),
                                       GTK_ACCESSIBLE_ROLE_PRESENTATION);
}

static void
fire_layer_init(FireLayer *self) {
  gtk_widget_set_can_target(GTK_WIDGET(self), FALSE);
  gtk_widget_set_focusable(GTK_WIDGET(self), FALSE);
  gtk_widget_set_overflow(GTK_WIDGET(self), GTK_OVERFLOW_VISIBLE);
}

GtkWidget *
fire_overlay_new(GtkWidget *content, GtkWidget *button, GtkWidget *owner) {
  GtkWidget *overlay = gtk_overlay_new();
  FireLayer *layer = g_object_new(TYPE_FIRE_LAYER, NULL);

  layer->button = button;
  if (button != NULL) {
    g_object_add_weak_pointer(G_OBJECT(button), (gpointer *)&layer->button);
  }
  gtk_overlay_set_child(GTK_OVERLAY(overlay), GTK_WIDGET(layer));
  /* Content is above the fire: labels and other controls stay unobscured. */
  gtk_overlay_add_overlay(GTK_OVERLAY(overlay), content);
  gtk_overlay_set_measure_overlay(GTK_OVERLAY(overlay), content, TRUE);
  gtk_overlay_set_clip_overlay(GTK_OVERLAY(overlay), content, FALSE);
  g_object_set_data_full(G_OBJECT(owner), "fire-layer", g_object_ref(layer),
                         g_object_unref);
  return overlay;
}

void
fire_overlay_set_preferences(GtkWidget *owner, gboolean animated,
                              gboolean visible) {
  FireLayer *self = g_object_get_data(G_OBJECT(owner), "fire-layer");

  if (self == NULL) {
    return;
  }
  self->visible = visible;
  self->animated = animated && visible;
  if (self->animated && self->tick_id == 0) {
    self->started = 0;
    self->elapsed = 0;
    self->tick_id = gtk_widget_add_tick_callback(
        GTK_WIDGET(self), fire_layer_tick, NULL, NULL);
  } else if (!self->animated && self->tick_id != 0) {
    gtk_widget_remove_tick_callback(GTK_WIDGET(self), self->tick_id);
    self->tick_id = 0;
  }
  if (!visible) {
    for (guint i = 0; i < G_N_ELEMENTS(self->cache); i++) {
      g_clear_object(&self->cache[i].texture);
      self->cache[i].used = 0;
    }
  }
  gtk_widget_queue_draw(GTK_WIDGET(self));
}
