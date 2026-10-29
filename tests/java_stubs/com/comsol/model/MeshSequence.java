package com.comsol.model;
public interface MeshSequence { MeshFeature create(String t, String type); MeshFeature feature(String t); void run(); double[][] getVertex(); }
