#ifndef FIRE_OVERLAY_H
#define FIRE_OVERLAY_H

#include <gtk/gtk.h>

GtkWidget *fire_overlay_new(GtkWidget *content, GtkWidget *button,
                            GtkWidget *owner);
void fire_overlay_set_preferences(GtkWidget *owner, gboolean animated,
                                   gboolean visible);

#endif
