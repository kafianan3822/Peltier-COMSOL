package com.comsol.model;
public interface EntList { Entity create(String t, String type); Entity create(String t); String[] tags(); void remove(String t); }
