#pragma once

#include <Eigen/Dense>
#include <array>
#include <string>
#include <vector>

#include "AHP_Class.h"

class TOPSIS_Class
{
public:
    static constexpr int CriteriaCount = AHP_Class::CriteriaCount;

    using Vector8 = AHP_Class::Vector8;
    using DecisionMatrix = Eigen::Matrix<double, Eigen::Dynamic, CriteriaCount>;

    enum class CriterionType
    {
        Benefit,
        Cost
    };

    struct TopsisResult
    {
        int Rank;
        int OriginalIndex;
        std::string PhoneName;

        double Score;
        double DistanceToIdeal;
        double DistanceToWorst;

        Vector8 WeightedNormalizedValues;
    };

public:
    TOPSIS_Class();

    void ClearPhones();

    /*
        Criterion order:
        Price, Battery, Camera, Performance, Storage, Weight, Charging, ScreenRatio
    */
    void AddPhone(
        const std::string& phoneName,
        double price,
        double battery,
        double camera,
        double performance,
        double storage,
        double weight,
        double charging,
        double screenRatio
    );

    /*
        This method is useful when the phone data is already stored as a matrix.
        Rows are phones, columns are criteria.
    */
    void SetDecisionMatrix(
        const std::vector<std::string>& phoneNames,
        const Eigen::MatrixXd& matrix
    );

    /*
        AHP already returns normalized weights, but this function also accepts
        raw positive weights and normalizes them.
    */
    void SetWeights(const Vector8& weights);

    /*
        Direct connection point between AHP and TOPSIS.
    */
    void SetWeightsFromAHP(const AHP_Class& ahp);

    /*
        Default criterion types:
        Price       -> Cost
        Battery     -> Benefit
        Camera      -> Benefit
        Performance -> Benefit
        Storage     -> Benefit
        Weight      -> Cost
        Charging    -> Benefit
        ScreenRatio -> Benefit
    */
    void SetCriterionType(
        AHP_Class::Criteria criterion,
        CriterionType type
    );

    CriterionType GetCriterionType(
        AHP_Class::Criteria criterion
    ) const;

    /*
        Runs the complete TOPSIS pipeline and returns phones sorted by score.
    */
    std::vector<TopsisResult> Rank();

    const std::vector<TopsisResult>& GetLastResults() const;

    const DecisionMatrix& GetDecisionMatrix() const;
    const DecisionMatrix& GetNormalizedMatrix() const;
    const DecisionMatrix& GetWeightedNormalizedMatrix() const;

    Vector8 GetWeights() const;
    Vector8 GetIdealBest() const;
    Vector8 GetIdealWorst() const;

private:
    std::vector<std::string> phoneNames_;

    DecisionMatrix decisionMatrix_;
    DecisionMatrix normalizedMatrix_;
    DecisionMatrix weightedNormalizedMatrix_;

    Vector8 weights_;
    Vector8 idealBest_;
    Vector8 idealWorst_;

    std::array<CriterionType, CriteriaCount> criterionTypes_;

    std::vector<TopsisResult> lastResults_;

private:
    void SetDefaultCriterionTypes();

    static int ToIndex(AHP_Class::Criteria criterion);

    static Vector8 NormalizeWeights(const Vector8& weights);

    void ValidateBeforeRanking() const;

    DecisionMatrix NormalizeDecisionMatrix() const;

    DecisionMatrix ApplyWeights(
        const DecisionMatrix& normalizedMatrix
    ) const;

    void CalculateIdealSolutions();

    Eigen::VectorXd CalculateDistancesTo(
        const Vector8& referenceVector
    ) const;

    Eigen::VectorXd CalculateClosenessScores(
        const Eigen::VectorXd& distancesToIdeal,
        const Eigen::VectorXd& distancesToWorst
    ) const;

    std::vector<TopsisResult> BuildSortedResults(
        const Eigen::VectorXd& scores,
        const Eigen::VectorXd& distancesToIdeal,
        const Eigen::VectorXd& distancesToWorst
    ) const;
};