import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000/api/v1";

export const fetchTickets = createAsyncThunk(
  "kanban/fetchTickets",
  async ({ projectName, status } = {}) => {
    const params = new URLSearchParams();
    if (projectName) params.append("project_name", projectName);
    if (status) params.append("status", status);
    const response = await axios.get(`${API_BASE}/tickets?${params.toString()}`);
    return response.data;
  }
);

export const fetchTicket = createAsyncThunk(
  "kanban/fetchTicket",
  async (ticketId) => {
    const response = await axios.get(`${API_BASE}/tickets/${ticketId}`);
    return response.data;
  }
);

export const updateTicketStatus = createAsyncThunk(
  "kanban/updateTicketStatus",
  async ({ ticketId, status }) => {
    const response = await axios.patch(`${API_BASE}/tickets/${ticketId}/status`, { status });
    return response.data;
  }
);

export const addTicketComment = createAsyncThunk(
  "kanban/addTicketComment",
  async ({ ticketId, body, authorType = "human" }) => {
    const response = await axios.post(`${API_BASE}/tickets/${ticketId}/comments`, { body, author_type: authorType });
    return response.data;
  }
);

export const fetchTicketComments = createAsyncThunk(
  "kanban/fetchTicketComments",
  async (ticketId) => {
    const response = await axios.get(`${API_BASE}/tickets/${ticketId}/comments`);
    return response.data;
  }
);

export const fetchTicketEvents = createAsyncThunk(
  "kanban/fetchTicketEvents",
  async (ticketId) => {
    const response = await axios.get(`${API_BASE}/tickets/${ticketId}/events`);
    return response.data;
  }
);

export const ingestTasks = createAsyncThunk(
  "kanban/ingestTasks",
  async ({ tasksDir, projectName } = {}) => {
    const response = await axios.post(`${API_BASE}/ingest`, { tasks_dir: tasksDir, project_name: projectName });
    return response.data;
  }
);

export const refineFromCommit = createAsyncThunk(
  "kanban/refineFromCommit",
  async ({ commitMessage, projectName }) => {
    const response = await axios.post(`${API_BASE}/commit-refine`, { commit_message: commitMessage, project_name: projectName });
    return response.data;
  }
);

export const fetchProgress = createAsyncThunk(
  "kanban/fetchProgress",
  async (projectName) => {
    const params = projectName ? `?project_name=${projectName}` : "";
    const response = await axios.get(`${API_BASE}/progress${params}`);
    return response.data;
  }
);

export const fetchDocPdf = createAsyncThunk(
  "kanban/fetchDocPdf",
  async (ticketId) => {
    const response = await axios.get(`${API_BASE}/tickets/${ticketId}/doc-pdf`, { responseType: "blob" });
    return response.data;
  }
);

const initialState = {
  tickets: [],
  todoTickets: [],
  inProgressTickets: [],
  doneTickets: [],
  selectedTicket: null,
  comments: [],
  events: [],
  progress: { total: 0, done: 0, in_progress: 0, todo: 0, progress_pct: 0 },
  loading: false,
  error: null,
  projectName: "001-task-management-api",
};

const kanbanSlice = createSlice({
  name: "kanban",
  initialState,
  reducers: {
    setProjectName: (state, action) => {
      state.projectName = action.payload;
    },
    setSelectedTicket: (state, action) => {
      state.selectedTicket = action.payload;
    },
    clearSelectedTicket: (state) => {
      state.selectedTicket = null;
      state.comments = [];
      state.events = [];
    },
    reorderTickets: (state, action) => {
      const { sourceStatus, destinationStatus, sourceIndex, destinationIndex } = action.payload;
      let sourceArray, destArray;
      
      switch (sourceStatus) {
        case "todo":
          sourceArray = state.todoTickets;
          break;
        case "in_progress":
          sourceArray = state.inProgressTickets;
          break;
        case "done":
          sourceArray = state.doneTickets;
          break;
      }
      
      switch (destinationStatus) {
        case "todo":
          destArray = state.todoTickets;
          break;
        case "in_progress":
          destArray = state.inProgressTickets;
          break;
        case "done":
          destArray = state.doneTickets;
          break;
      }
      
      if (sourceArray === destArray) {
        const [removed] = sourceArray.splice(sourceIndex, 1);
        sourceArray.splice(destinationIndex, 0, removed);
      } else {
        const [removed] = sourceArray.splice(sourceIndex, 1);
        removed.status = destinationStatus;
        destArray.splice(destinationIndex, 0, removed);
      }
      
      state.tickets = [...state.todoTickets, ...state.inProgressTickets, ...state.doneTickets];
    },
    updateTicketInState: (state, action) => {
      const updated = action.payload;
      const index = state.tickets.findIndex(t => t.id === updated.id);
      if (index !== -1) {
        state.tickets[index] = updated;
      }
      state.todoTickets = state.tickets.filter(t => t.status === "todo").sort((a, b) => a.position - b.position);
      state.inProgressTickets = state.tickets.filter(t => t.status === "in_progress").sort((a, b) => a.position - b.position);
      state.doneTickets = state.tickets.filter(t => t.status === "done").sort((a, b) => a.position - b.position);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTickets.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTickets.fulfilled, (state, action) => {
        state.loading = false;
        state.tickets = action.payload;
        state.todoTickets = action.payload.filter(t => t.status === "todo").sort((a, b) => a.position - b.position);
        state.inProgressTickets = action.payload.filter(t => t.status === "in_progress").sort((a, b) => a.position - b.position);
        state.doneTickets = action.payload.filter(t => t.status === "done").sort((a, b) => a.position - b.position);
      })
      .addCase(fetchTickets.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(fetchTicket.fulfilled, (state, action) => {
        state.selectedTicket = action.payload;
      })
      .addCase(updateTicketStatus.fulfilled, (state, action) => {
        const updated = action.payload;
        const index = state.tickets.findIndex(t => t.id === updated.id);
        if (index !== -1) {
          state.tickets[index] = updated;
        }
        state.todoTickets = state.tickets.filter(t => t.status === "todo").sort((a, b) => a.position - b.position);
        state.inProgressTickets = state.tickets.filter(t => t.status === "in_progress").sort((a, b) => a.position - b.position);
        state.doneTickets = state.tickets.filter(t => t.status === "done").sort((a, b) => a.position - b.position);
        if (state.selectedTicket?.id === updated.id) {
          state.selectedTicket = updated;
        }
      })
      .addCase(addTicketComment.fulfilled, (state, action) => {
        state.comments.push(action.payload);
      })
      .addCase(fetchTicketComments.fulfilled, (state, action) => {
        state.comments = action.payload;
      })
      .addCase(fetchTicketEvents.fulfilled, (state, action) => {
        state.events = action.payload;
      })
      .addCase(ingestTasks.fulfilled, (state, action) => {
        state.tickets = action.payload;
        state.todoTickets = action.payload.filter(t => t.status === "todo").sort((a, b) => a.position - b.position);
        state.inProgressTickets = action.payload.filter(t => t.status === "in_progress").sort((a, b) => a.position - b.position);
        state.doneTickets = action.payload.filter(t => t.status === "done").sort((a, b) => a.position - b.position);
      })
      .addCase(fetchProgress.fulfilled, (state, action) => {
        state.progress = action.payload;
      });
  },
});

export const { setProjectName, setSelectedTicket, clearSelectedTicket, reorderTickets, updateTicketInState } = kanbanSlice.actions;
export default kanbanSlice.reducer;