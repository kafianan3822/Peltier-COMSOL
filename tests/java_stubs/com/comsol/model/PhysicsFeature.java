package com.comsol.model;
public interface PhysicsFeature extends Entity { FList feature(); PhysicsFeature feature(String t); PhysicsFeature create(String t, String type, int dim); }
