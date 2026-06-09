requireAuth();

const feedbackEl = document.getElementById("dashboard-feedback");
const emptyEl = document.getElementById("dashboard-empty");
const chartEl = document.getElementById("dashboard-chart");

const feedback2El = document.getElementById("dashboard-feedback-2");
const empty2El = document.getElementById("dashboard-empty-2");
const chart2El = document.getElementById("dashboard-chart-2");

const feedback3El = document.getElementById("dashboard-feedback-3");
const empty3El = document.getElementById("dashboard-empty-3");
const chart3El = document.getElementById("dashboard-chart-3");
const dashboardTimeUnitFilterEl = document.getElementById("dashboard-time-unit-filter");
const routineTypeFilterEl = document.getElementById("routine-type-filter");
const routineTypeFilterTriggerEl = document.getElementById("routine-type-filter-trigger");
const routineTypeFilterSummaryEl = document.getElementById("routine-type-filter-summary");
const routineTypeFilterMenuEl = document.getElementById("routine-type-filter-menu");
const routineYearFilterEl = document.getElementById("routine-year-filter");
const routineMonthFilterEl = document.getElementById("routine-month-filter");
const routineUserFilterEl = document.getElementById("routine-user-filter");

const projectMonthlyFeedbackEl = document.getElementById("project-monthly-feedback");
const projectMonthlyYearFilterEl = document.getElementById("project-monthly-year-filter");
const projectMonthlyMonthFilterEl = document.getElementById("project-monthly-month-filter");
const projectMonthlyTypeFilterEl = document.getElementById("project-monthly-type-filter");
const projectMonthlyUserFilterEl = document.getElementById("project-monthly-user-filter");

const feedback4El = document.getElementById("dashboard-feedback-4");
const empty4El = document.getElementById("dashboard-empty-4");
const chart4El = document.getElementById("dashboard-chart-4");

const feedback5El = document.getElementById("dashboard-feedback-5");
const empty5El = document.getElementById("dashboard-empty-5");
const chart5El = document.getElementById("dashboard-chart-5");

const feedback6El = document.getElementById("dashboard-feedback-6");
const empty6El = document.getElementById("dashboard-empty-6");
const chart6El = document.getElementById("dashboard-chart-6");

const feedback7El = document.getElementById("dashboard-feedback-7");
const empty7El = document.getElementById("dashboard-empty-7");
const chart7El = document.getElementById("dashboard-chart-7");

const feedback8El = document.getElementById("dashboard-feedback-8");
const empty8El = document.getElementById("dashboard-empty-8");
const chart8El = document.getElementById("dashboard-chart-8");

const feedback9El = document.getElementById("dashboard-feedback-9");
const empty9El = document.getElementById("dashboard-empty-9");
const chart9El = document.getElementById("dashboard-chart-9");
const complexityMonthlyYearFilterEl = document.getElementById("complexity-monthly-year-filter");
const complexityMonthlyMonthFilterEl = document.getElementById("complexity-monthly-month-filter");
const complexityMonthlyTypeFilterEl = document.getElementById("complexity-monthly-type-filter");
const complexityMonthlyUserFilterEl = document.getElementById("complexity-monthly-user-filter");

const feedback10El = document.getElementById("dashboard-feedback-10");
const empty10El = document.getElementById("dashboard-empty-10");
const chart10El = document.getElementById("dashboard-chart-10");
const earnedValueYearFilterEl = document.getElementById("earned-value-year-filter");
const earnedValueMonthFilterEl = document.getElementById("earned-value-month-filter");
const earnedValueTypeFilterEl = document.getElementById("earned-value-type-filter");
const earnedValueUserFilterEl = document.getElementById("earned-value-user-filter");

const feedback11El = document.getElementById("dashboard-feedback-11");
const empty11El = document.getElementById("dashboard-empty-11");
const chart11El = document.getElementById("dashboard-chart-11");
const schedulePerformanceYearFilterEl = document.getElementById("schedule-performance-year-filter");
const schedulePerformanceMonthFilterEl = document.getElementById("schedule-performance-month-filter");
const schedulePerformanceTypeFilterEl = document.getElementById("schedule-performance-type-filter");
const schedulePerformanceUserFilterEl = document.getElementById("schedule-performance-user-filter");

const feedback12El = document.getElementById("dashboard-feedback-12");
const empty12El = document.getElementById("dashboard-empty-12");
const chart12El = document.getElementById("dashboard-chart-12");
const costPerformanceYearFilterEl = document.getElementById("cost-performance-year-filter");
const costPerformanceMonthFilterEl = document.getElementById("cost-performance-month-filter");
const costPerformanceTypeFilterEl = document.getElementById("cost-performance-type-filter");
const costPerformanceUserFilterEl = document.getElementById("cost-performance-user-filter");

const feedback13El = document.getElementById("dashboard-feedback-13");
const empty13El = document.getElementById("dashboard-empty-13");
const chart13El = document.getElementById("dashboard-chart-13");
const effortDeviationYearFilterEl = document.getElementById("effort-deviation-year-filter");
const effortDeviationMonthFilterEl = document.getElementById("effort-deviation-month-filter");
const effortDeviationTypeFilterEl = document.getElementById("effort-deviation-type-filter");
const effortDeviationUserFilterEl = document.getElementById("effort-deviation-user-filter");

const feedback14El = document.getElementById("dashboard-feedback-14");
const empty14El = document.getElementById("dashboard-empty-14");
const chart14El = document.getElementById("dashboard-chart-14");
const newProcessResponsibleFilterEl = document.getElementById("new-process-responsible-filter");
const newProcessYearFilterEl = document.getElementById("new-process-year-filter");
const newProcessMonthFilterEl = document.getElementById("new-process-month-filter");

const refreshBtn = document.getElementById("refresh-btn");

let routineItems = [];
let projectMonthlyItems = [];
let avgRealItems = [];
let complexityMonthlyItems = [];
let earnedValueItems = [];
let effortDeviationItems = [];
let newProcessTimeItems = [];

function setFeedback(target, message, type = "status") {
  target.textContent = message || "";
  target.className = type;
}

function showState(emptyTarget, chartTarget, { showEmpty = false, showChart = false }) {
  emptyTarget.classList.toggle("hidden", !showEmpty);
  chartTarget.classList.toggle("hidden", !showChart);
}
