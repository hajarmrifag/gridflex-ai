Feature: Recover from an optimizer failure without restarting the service
  An analyst needs an actionable error instead of a partial optimization,
  and must be able to retry after the solver becomes available again.

  Scenario Outline: A failed solver releases capacity and does not poison the cache
    Given a valid synthetic optimization request
    When the solver reports <failure> during the <stage> solve
    Then the API returns an actionable 422 without internal solver details
    And both compute slots remain available
    And retrying the same request with the real solver succeeds

    Examples:
      | failure    | stage      |
      | time limit | peak       |
      | infeasible | peak       |
      | time limit | throughput |
