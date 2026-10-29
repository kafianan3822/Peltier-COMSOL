package com.comsol.model;
public interface SolverFeature extends Entity { FList feature(); SolverFeature feature(String t); SolverFeature create(String t, String type); }
