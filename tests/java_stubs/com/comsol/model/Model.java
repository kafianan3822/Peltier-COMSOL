package com.comsol.model;
public interface Model {
  ModelParam param(); CompList component(); ModelNode component(String t);
  EntList func(); Entity func(String t); StudyList study(); Study study(String t);
  SolList sol(); SolverSequence sol(String t); Results result(); void save(String p); Model label(String l);
}
