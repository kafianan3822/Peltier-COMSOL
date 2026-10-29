package com.comsol.model;
public interface ModelParam { void set(String n, String e); void set(String n, String e, String d); double evaluate(String e); }
