package com.comsol.model;
public interface Physics { Entity prop(String t); PhysicsFeature feature(String t); PhysicsFeature create(String t, String type, int dim); }
