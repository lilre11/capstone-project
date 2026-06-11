#pragma once
#include <Eigen/Dense>
class AHP_Class
{
public :
	enum Criteria { Price, 
		Battery, 
		Camera, 
		Performance, 
		Storage, 
		Weight, 
		Charging, 
		ScreenRatio};
	float CriteriaWeights[8];

};

