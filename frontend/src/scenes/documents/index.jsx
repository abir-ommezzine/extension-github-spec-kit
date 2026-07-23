import { useState } from "react";
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
  Tabs,
  Tab,
  Chip,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { tokens } from "../../theme";
import { mockDataDocuments } from "../../data/mockData";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import CloseIcon from "@mui/icons-material/Close";
import AssessmentIcon from "@mui/icons-material/Assessment";
import Header from "../../components/Header";

const agentLabels = {
  parsing: "Parsing Agent",
  summary: "Summary Agent",
  glossary: "Glossary Agent",
  diagram: "Diagram Agent",
  docWriter: "Documentation Writer Agent",
  layout: "Layout Agent",
};

const agentColors = {
  parsing: "#4caf50",
  summary: "#2196f3",
  glossary: "#ff9800",
  diagram: "#e91e63",
  docWriter: "#9c27b0",
  layout: "#00bcd4",
};

const formatKey = (key) =>
  key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

const getValueColor = (key, value) => {
  if (typeof value !== "number") return "inherit";
  if (key.includes("rate") || key.includes("score") || key.includes("adherence") || key.includes("index")) {
    if (value >= 90) return "#4caf50";
    if (value >= 75) return "#ff9800";
    return "#f44336";
  }
  return "inherit";
};

const KpiPopup = ({ open, onClose, document }) => {
  const theme = useTheme();
  const colors = tokens(theme.palette.mode);
  const [tabIndex, setTabIndex] = useState(0);
  const agentKeys = Object.keys(document?.agentEvaluations || {});
  const currentAgent = agentKeys[tabIndex];
  const agentData = document?.agentEvaluations?.[currentAgent];

  if (!agentData) return null;

  const techEval = agentData.technical_evaluation || {};
  const pmKpis = agentData.project_management_kpis || {};

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
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
        <Box>
          <Typography variant="h3" fontWeight="bold" color={colors.grey[100]}>
            KPI Metrics
          </Typography>
          <Typography variant="h6" color={colors.greenAccent[400]} sx={{ mt: "5px" }}>
            {document?.name} — Score: {document?.kpi}%
          </Typography>
        </Box>
        <IconButton onClick={onClose}>
          <CloseIcon sx={{ color: colors.grey[100] }} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        <Tabs
          value={tabIndex}
          onChange={(_, v) => setTabIndex(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            borderBottom: `1px solid ${colors.grey[700]}`,
            "& .MuiTab-root": { color: colors.grey[300] },
            "& .Mui-selected": { color: `${colors.greenAccent[500]} !important` },
            "& .MuiTabs-indicator": { backgroundColor: colors.greenAccent[500] },
          }}
        >
          {agentKeys.map((key) => (
            <Tab
              key={key}
              label={
                <Box display="flex" alignItems="center" gap={1}>
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      backgroundColor: agentColors[key],
                    }}
                  />
                  {agentLabels[key] || key}
                </Box>
              }
            />
          ))}
        </Tabs>

        <Box p={3}>
          <Typography variant="h5" fontWeight="bold" color={colors.greenAccent[400]} mb={2}>
            {agentLabels[currentAgent] || currentAgent}
          </Typography>

          <Box mb={3}>
            <Typography variant="h6" fontWeight="bold" color={colors.grey[100]} mb={1}>
              Technical Evaluation
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
                  {Object.entries(techEval).map(([key, value]) => (
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
                          <Typography fontWeight="bold" sx={{ color: getValueColor(key, value) }}>
                            {value}{key.includes("rate") || key.includes("score") || key.includes("adherence") || key.includes("index") ? "%" : ""}
                          </Typography>
                        ) : (
                          <Chip
                            label={value}
                            size="small"
                            sx={{
                              backgroundColor:
                                value === "READY_FOR_EXECUTION" || value === "READY_FOR_PUBLICATION" || value === "READY_FOR_ANCHORING"
                                  ? colors.greenAccent[600]
                                  : value === "BLOCKED"
                                  ? colors.redAccent ? colors.redAccent[500] : "#f44336"
                                  : colors.blueAccent[700],
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

          <Box>
            <Typography variant="h6" fontWeight="bold" color={colors.grey[100]} mb={1}>
              Project Management KPIs
            </Typography>
            <TableContainer
              component={Paper}
              sx={{ backgroundColor: colors.primary[400], borderRadius: "8px" }}
            >
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ color: colors.grey[300], borderBottom: `1px solid ${colors.grey[700]}` }}>
                      KPI
                    </TableCell>
                    <TableCell sx={{ color: colors.grey[300], borderBottom: `1px solid ${colors.grey[700]}` }} align="right">
                      Value
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(pmKpis).map(([key, value]) => (
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
                          <Typography fontWeight="bold" sx={{ color: getValueColor(key, value) }}>
                            {value}{key.includes("score") || key.includes("index") ? "%" : ""}
                          </Typography>
                        ) : (
                          <Chip
                            label={value}
                            size="small"
                            sx={{
                              backgroundColor:
                                value === "READY_FOR_EXECUTION" || value === "READY_FOR_PUBLICATION"
                                  ? colors.greenAccent[600]
                                  : value === "ÉLEVÉ"
                                  ? colors.redAccent ? colors.redAccent[500] : "#f44336"
                                  : value === "MOYEN"
                                  ? colors.orange ? colors.orange[500] : "#ff9800"
                                  : colors.blueAccent[700],
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
        </Box>
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

  const columns = [
    { field: "id", headerName: "ID" },
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
      flex: 1,
    },
    {
      field: "kpi",
      headerName: "KPI",
      flex: 1,
      renderCell: ({ row }) => {
        const score = row.kpi;
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
      flex: 1,
      renderCell: () => {
        return (
          <Box
            width="60%"
            m="0 auto"
            p="5px"
            display="flex"
            justifyContent="center"
            alignItems="center"
            backgroundColor={colors.greenAccent[600]}
            borderRadius="4px"
            sx={{ cursor: "pointer" }}
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
        <DataGrid checkboxSelection rows={mockDataDocuments} columns={columns} />
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
