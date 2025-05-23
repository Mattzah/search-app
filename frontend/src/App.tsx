import React, { useState } from "react";
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
} from "@mui/material";
import { createTheme, ThemeProvider } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2",
    },
  },
});

function App() {
  const [directions, setDirections] = useState("");

  return (
    <ThemeProvider theme={theme}>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Box sx={{ display: "flex", gap: 3, height: "90vh" }}>
          {/* Left Panel - Input */}
          <Box sx={{ flex: 1 }}>
            <Paper
              sx={{
                p: 3,
                height: "100%",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Typography variant="h6" gutterBottom>
                Initial Input
              </Typography>

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  Directions:
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  placeholder="Insert text that provides directions for document"
                  value={directions}
                  onChange={(e) => setDirections(e.target.value)}
                  variant="outlined"
                />
              </Box>

              <Button
                variant="contained"
                sx={{ mb: 4, alignSelf: "flex-start" }}
              >
                CREATE QUERIES
              </Button>

              <Box sx={{ mt: "auto" }}>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  Search Using Queries:
                </Typography>
                <Button variant="contained" sx={{ alignSelf: "flex-start" }}>
                  SEARCH
                </Button>
              </Box>
            </Paper>
          </Box>

          {/* Right Panel - Output */}
          <Box sx={{ flex: 1 }}>
            <Paper
              sx={{
                p: 3,
                height: "100%",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Typography variant="h6" gutterBottom>
                Output
              </Typography>

              {/* This will be populated with search queries and results */}
              <Box
                sx={{
                  flexGrow: 1,
                  backgroundColor: "#f5f5f5",
                  borderRadius: 1,
                  p: 2,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  Output will appear here
                </Typography>
              </Box>
            </Paper>
          </Box>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
