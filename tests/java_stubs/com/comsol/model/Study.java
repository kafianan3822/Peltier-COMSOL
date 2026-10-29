package com.comsol.model;
public interface Study { StudyFeature create(String t, String type); StudyFeature feature(String t); FList feature(); void run(); void createAutoSequences(String s); Study label(String l); }
