import { useState, useEffect, useRef } from "react";
import {
  Box,
  Typography,
  useTheme,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { tokens } from "../../theme";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import CloseIcon from "@mui/icons-material/Close";
import AssessmentIcon from "@mui/icons-material/Assessment";
import Header from "../../components/Header";

const API_BASE = "http://localhost:8000/api/v1/docs";
const POLL_INTERVAL = 3000;
const ACTIVE_STATUSES = ["parsing", "summary", "glossary", "diagram", "writing", "layout", "rendering", "pending"];

const agentDisplayNames = [
  { key: "Parsing", evalKey: "parsing", color: "#4caf50" },
  { key: "Summary", evalKey: "summary", color: "#2196f3" },
  { key: "Glossary", evalKey: "glossary", color: "#ff9800" },
  { key: "Diagram", evalKey: "diagram", color: "#e91e63" },
  { key: "Doc Writer", evalKey: "docWriter", color: "#9c27b0" },
  { key: "Layout", evalKey: "layout", color: "#00bcd4" },
];

const getScoreColor = (score, colors) => {
  if (score == null) return colors.grey[600];
  if (score >= 90) return colors.greenAccent[600];
  if (score >= 75) return "#ff9800";
  return colors.redAccent ? colors.redAccent[500] : "#f44336";
};

const formatKey = (key) =>
  key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const AgentDetailView = ({ agentName, agentColor, evalData, colors }) => {
  if (!evalData) {
    return (
      <Typography color={colors.grey[500]} sx={{ mt: 2, textAlign: "center" }}>
        No evaluation data available yet.
      </Typography>
    );
  }

  const techEval = evalData.technical_evaluation || {};
  const pmKpis = evalData.project_management_kpis || {};

  const filterEntries = (obj) =>
    Object.entries(obj).filter(
      ([, v]) => v !== null && v !== undefined && typeof v !== "object"
    );

  const filteredTech = filterEntries(techEval);
  const filteredPm = filterEntries(pmKpis);

  const renderTable = (title, entries) => {
    if (entries.length === 0) return null;
    return (
      <Box mb={3}>
        <Typography variant="h6" fontWeight="bold" color={colors.grey[100]} mb={1}>
          {title}
        </Typography>
        <TableContainer
          component={Paper}
          sx={{ backgroundColor: colors.primary[400], borderRadius: "8px" }}
        >
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: colors.grey[300], borderBottom: `1px solid ${colors.grey[700]}` }}>
                  Metric
                </TableCell>
                <TableCell sx={{ color: colors.grey[300], borderBottom: `1px solid ${colors.grey[700]}` }} align="right">
                  Value
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {entries.map(([key, value]) => (
                <TableRow key={key}>
                  <TableCell sx={{ color: colors.grey[100], borderBottom: `1px solid ${colors.grey[700]}` }}>
                    {formatKey(key)}
                  </TableCell>
                  <TableCell sx={{ borderBottom: `1px solid ${colors.grey[700]}` }} align="right">
                    {typeof value === "boolean" ? (
                      <Chip
                        label={value ? "Yes" : "No"}
                        size="small"
                        sx={{
                          backgroundColor: value ? colors.greenAccent[600] : colors.redAccent ? colors.redAccent[500] : "#f44336",
                          color: colors.grey[100],
                        }}
                      />
                    ) : typeof value === "number" ? (
                      <Typography fontWeight="bold" sx={{ color: getScoreColor(value, colors) }}>
                        {value}{key.includes("rate") || key.includes("score") || key.includes("adherence") || key.includes("index") ? "%" : ""}
                      </Typography>
                    ) : (
                      <Chip
                        label={String(value)}
                        size="small"
                        sx={{
                          backgroundColor: colors.blueAccent[700],
                          color: colors.grey[100],
                        }}
                      />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    );
  };

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <Box sx={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: agentColor }} />
        <Typography variant="h5" fontWeight="bold" color={colors.grey[100]}>
          {agentName}
        </Typography>
      </Box>
      {renderTable("Technical Evaluation", filteredTech)}
      {renderTable("Project Management KPIs", filteredPm)}
    </Box>
  );
};

const KpiPopup = ({ open, onClose, document }) => {
  const theme = useTheme();
  const colors = tokens(theme.palette.mode);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentEvaluations, setAgentEvaluations] = useState(null);
  const [loadingEvals, setLoadingEvals] = useState(false);

  const agentScores = document?.agentScores || {};
  const pipelineRunId = document?.pipeline_run_id;

  useEffect(() => {
    if (open && pipelineRunId) {
      setLoadingEvals(true);
      fetch(`${API_BASE}/pipeline-run/${pipelineRunId}/evaluations`)
        .then((res) => res.json())
        .then((data) => setAgentEvaluations(data.agentEvaluations || {}))
        .catch(() => setAgentEvaluations({}))
        .finally(() => setLoadingEvals(false));
    }
    if (!open) {
      setSelectedAgent(null);
      setAgentEvaluations(null);
    }
  }, [open, pipelineRunId]);

  const selectedAgentInfo = agentDisplayNames.find((a) => a.key === selectedAgent);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          backgroundColor: colors.primary[400],
          borderRadius: "10px",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: `1px solid ${colors.grey[700]}`,
        }}
      >
        <Box display="flex" alignItems="center" gap={1}>
          {selectedAgent && (
            <IconButton
              onClick={() => setSelectedAgent(null)}
              size="small"
              sx={{ color: colors.greenAccent[400] }}
            >
              <ArrowBackIcon />
            </IconButton>
          )}
          <Box>
            <Typography variant="h3" fontWeight="bold" color={colors.grey[100]}>
              {selectedAgent || "Agent Scores"}
            </Typography>
            <Typography variant="h6" color={colors.greenAccent[400]} sx={{ mt: "5px" }}>
              {document?.name} — Global: {document?.kpi != null ? `${document.kpi}%` : "--"}
            </Typography>
          </Box>
        </Box>
        <IconButton onClick={onClose}>
          <CloseIcon sx={{ color: colors.grey[100] }} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: "20px !important" }}>
        {selectedAgent ? (
          <AgentDetailView
            agentName={selectedAgent}
            agentColor={selectedAgentInfo?.color || colors.grey[600]}
            evalData={agentEvaluations?.[selectedAgentInfo?.evalKey]}
            colors={colors}
          />
        ) : (
          <TableContainer
            component={Paper}
            sx={{ backgroundColor: colors.primary[400], borderRadius: "8px" }}
          >
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ color: colors.grey[300], borderBottom: `1px solid ${colors.grey[700]}`, fontWeight: "bold" }}>
                    Agent
                  </TableCell>
                  <TableCell
                    sx={{ color: colors.grey[300], borderBottom: `1px solid ${colors.grey[700]}`, fontWeight: "bold" }}
                    align="right"
                  >
                    Score
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {agentDisplayNames.map(({ key, color }) => {
                  const score = agentScores[key];
                  return (
                    <TableRow
                      key={key}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => setSelectedAgent(key)}
                    >
                      <TableCell sx={{ color: colors.grey[100], borderBottom: `1px solid ${colors.grey[700]}` }}>
                        <Box display="flex" alignItems="center" gap={1}>
                          <Box
                            sx={{
                              width: 10,
                              height: 10,
                              borderRadius: "50%",
                              backgroundColor: color,
                              flexShrink: 0,
                            }}
                          />
                          {key}
                        </Box>
                      </TableCell>
                      <TableCell sx={{ borderBottom: `1px solid ${colors.grey[700]}` }} align="right">
                        {score != null ? (
                          <Chip
                            label={`${score}%`}
                            size="small"
                            sx={{
                              backgroundColor: getScoreColor(score, colors),
                              color: colors.grey[100],
                              fontWeight: "bold",
                              minWidth: "60px",
                            }}
                          />
                        ) : (
                          <Typography color={colors.grey[500]}>--</Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {loadingEvals && (
          <Box display="flex" justifyContent="center" mt={2}>
            <Typography color={colors.grey[500]}>Loading evaluations...</Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ borderTop: `1px solid ${colors.grey[700]}`, p: "16px !important" }}>
        <Button
          onClick={onClose}
          sx={{
            backgroundColor: colors.greenAccent[600],
            color: colors.grey[100],
            "&:hover": { backgroundColor: colors.greenAccent[700] },
          }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const Documents = () => {
  const theme = useTheme();
  const colors = tokens(theme.palette.mode);
  const [kpiPopup, setKpiPopup] = useState({ open: false, document: null });
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef(null);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE}/documents`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    pollRef.current = setInterval(() => {
      fetchDocuments();
    }, POLL_INTERVAL);
    return () => clearInterval(pollRef.current);
  }, []);

  const handleViewPdf = (docVersionId) => {
    if (docVersionId) {
      window.open(`${API_BASE}/pdf/${docVersionId}`, "_blank");
    }
  };

  const columns = [
    { field: "id", headerName: "ID", width: 80 },
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      cellClassName: "name-column--cell",
    },
    {
      field: "projectName",
      headerName: "Project Name",
      flex: 1,
    },
    {
      field: "version",
      headerName: "Version",
      flex: 0.5,
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      renderCell: ({ row: { status } }) => {
        let bgColor;
        switch (status) {
          case "completed":
            bgColor = colors.greenAccent[600];
            break;
          case "parsing":
            bgColor = colors.blueAccent[700];
            break;
          case "summary":
            bgColor = "#2196f3";
            break;
          case "glossary":
            bgColor = "#ff9800";
            break;
          case "diagram":
            bgColor = "#e91e63";
            break;
          case "writing":
            bgColor = "#9c27b0";
            break;
          case "layout":
          case "rendering":
            bgColor = "#00bcd4";
            break;
          case "failed":
            bgColor = colors.redAccent ? colors.redAccent[500] : "#f44336";
            break;
          case "pending":
            bgColor = colors.grey[600];
            break;
          default:
            bgColor = colors.grey[600];
        }
        return (
          <Box
            width="80%"
            m="0 auto"
            p="5px"
            display="flex"
            justifyContent="center"
            backgroundColor={bgColor}
            borderRadius="4px"
          >
            <Typography color={colors.grey[100]} sx={{ ml: "5px" }}>
              {status}
            </Typography>
          </Box>
        );
      },
    },
    {
      field: "kpi",
      headerName: "KPI",
      flex: 0.7,
      renderCell: ({ row }) => {
        const score = row.kpi;
        if (score == null) {
          return (
            <Box
              width="60%"
              m="0 auto"
              p="5px"
              display="flex"
              justifyContent="center"
              alignItems="center"
              backgroundColor={colors.grey[600]}
              borderRadius="4px"
            >
              <Typography color={colors.grey[300]} sx={{ ml: "5px" }}>
                --
              </Typography>
            </Box>
          );
        }
        let bgColor = colors.greenAccent[600];
        if (score < 80) bgColor = colors.redAccent ? colors.redAccent[500] : "#f44336";
        else if (score < 90) bgColor = "#ff9800";

        return (
          <Box
            width="60%"
            m="0 auto"
            p="5px"
            display="flex"
            justifyContent="center"
            alignItems="center"
            backgroundColor={bgColor}
            borderRadius="4px"
            sx={{ cursor: "pointer" }}
            onClick={() => setKpiPopup({ open: true, document: row })}
          >
            <AssessmentIcon sx={{ mr: "5px" }} />
            <Typography color={colors.grey[100]} sx={{ ml: "5px" }}>
              {score}%
            </Typography>
          </Box>
        );
      },
    },
    {
      field: "viewer",
      headerName: "Viewer",
      flex: 0.7,
      renderCell: ({ row }) => {
        const hasPdf = !!row.doc_version_id;
        return (
          <Box
            width="60%"
            m="0 auto"
            p="5px"
            display="flex"
            justifyContent="center"
            alignItems="center"
            backgroundColor={hasPdf ? colors.greenAccent[600] : colors.grey[600]}
            borderRadius="4px"
            sx={{ cursor: hasPdf ? "pointer" : "default" }}
            onClick={() => hasPdf && handleViewPdf(row.doc_version_id)}
          >
            <VisibilityOutlinedIcon />
            <Typography color={colors.grey[100]} sx={{ ml: "5px" }}>
              view
            </Typography>
          </Box>
        );
      },
    },
  ];

  return (
    <Box m="20px">
      <Header title="DOCUMENTS" subtitle="Managing the Documents" />
      <Box
        m="40px 0 0 0"
        height="75vh"
        sx={{
          "& .MuiDataGrid-root": {
            border: "none",
          },
          "& .MuiDataGrid-cell": {
            borderBottom: "none",
          },
          "& .name-column--cell": {
            color: colors.greenAccent[300],
          },
          "& .MuiDataGrid-columnHeaders": {
            backgroundColor: colors.blueAccent[700],
            borderBottom: "none",
          },
          "& .MuiDataGrid-virtualScroller": {
            backgroundColor: colors.primary[400],
          },
          "& .MuiDataGrid-footerContainer": {
            borderTop: "none",
            backgroundColor: colors.blueAccent[700],
          },
          "& .MuiCheckbox-root": {
            color: `${colors.greenAccent[200]} !important`,
          },
        }}
      >
        <DataGrid
          checkboxSelection
          rows={documents}
          columns={columns}
          loading={loading}
          getRowId={(row) => row.id}
        />
      </Box>

      <KpiPopup
        open={kpiPopup.open}
        onClose={() => setKpiPopup({ open: false, document: null })}
        document={kpiPopup.document}
      />
    </Box>
  );
};

export default Documents;
