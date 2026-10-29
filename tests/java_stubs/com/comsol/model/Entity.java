package com.comsol.model;
public interface Entity {
  Entity set(String p, String v); Entity set(String p, String[] v); Entity set(String p, int v);
  Entity set(String p, double v); Entity set(String p, boolean v);
  Entity set(String p, String v, String d);
  String getString(String p); String[] getStringArray(String p); boolean getBoolean(String p);
  String getType(); String label(); Entity label(String l); Entity active(boolean a);
  Selection selection(); String[] properties();
}
