package com.comsol.model;
public interface GeomSequence { Entity create(String t, String type); Entity feature(String t); void run(); int getNDomains(); int getNBoundaries(); }
