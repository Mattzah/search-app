import React, { useState } from "react";
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Link,
} from "@mui/material";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { Search, AutoAwesome } from "@mui/icons-material";

const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2",
    },
  },
});

interface SearchQuery {
  query: string;
  category: string;
}

interface SourceSummary {
  title: string;
  url: string;
  source_summary: string[];
  domain: string;
  date_accessed: string;
}

interface SearchResponse {
  queries: SearchQuery[];
  summary: string[];
  sources: SourceSummary[];
  processing_time: number;
}

function App() {
  const [subject, setSubject] = useState("");
  const [purpose, setPurpose] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);

  const handleSearch = async () => {
    if (!subject.trim() || !purpose.trim()) {
      setError("Subject and Purpose are required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        "http://localhost:8000/search-and-summarize",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            subject: subject.trim(),
            purpose: purpose.trim(),
            jurisdiction: jurisdiction.trim() || null,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data: SearchResponse = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const clearResults = () => {
    setResults(null);
    setError(null);
  };

  return (
    <ThemeProvider theme={theme}>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
          Government Document Research Assistant
        </Typography>

        <Box sx={{ display: "flex", gap: 3, height: "85vh" }}>
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
                Document Requirements
              </Typography>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Subject *
                </Typography>
                <TextField
                  fullWidth
                  placeholder="e.g., Housing affordability crisis"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  variant="outlined"
                  size="medium"
                />
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Purpose *
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={2}
                  placeholder="e.g., Policy briefing for Minister on current housing initiatives"
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  variant="outlined"
                />
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Jurisdiction (optional)
                </Typography>
                <TextField
                  fullWidth
                  placeholder="e.g., Canada, Ontario, City of Toronto"
                  value={jurisdiction}
                  onChange={(e) => setJurisdiction(e.target.value)}
                  variant="outlined"
                />
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  variant="contained"
                  startIcon={
                    loading ? (
                      <CircularProgress size={16} color="inherit" />
                    ) : (
                      <Search />
                    )
                  }
                  onClick={handleSearch}
                  disabled={loading}
                  sx={{ flex: 1 }}
                >
                  {loading ? "Researching..." : "Research & Summarize"}
                </Button>

                {results && (
                  <Button
                    variant="outlined"
                    onClick={clearResults}
                    disabled={loading}
                  >
                    Clear
                  </Button>
                )}
              </Box>

              {loading && (
                <Box sx={{ mt: 2, textAlign: "center" }}>
                  <Typography variant="body2" color="text.secondary">
                    Generating queries, searching web, extracting content, and
                    creating summary...
                  </Typography>
                </Box>
              )}
            </Paper>
          </Box>

          {/* Right Panel - Results */}
          <Box sx={{ flex: 1 }}>
            <Paper
              sx={{
                p: 3,
                height: "100%",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              <Typography variant="h6" gutterBottom>
                Research Results
              </Typography>

              {results ? (
                <Box sx={{ flexGrow: 1, overflow: "auto" }}>
                  {/* Processing Time */}
                  <Box sx={{ mb: 2 }}>
                    <Chip
                      label={`Processed in ${results.processing_time.toFixed(
                        1
                      )}s`}
                      size="small"
                      color="success"
                      icon={<AutoAwesome />}
                    />
                  </Box>

                  {/* Search Queries Used */}
                  <Typography
                    variant="subtitle2"
                    sx={{ mb: 1, fontWeight: 600 }}
                  >
                    Search Queries Generated:
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    {results.queries.map((query, index) => (
                      <Chip
                        key={index}
                        label={`${query.category}: ${query.query}`}
                        variant="outlined"
                        size="small"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    ))}
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  {/* Key Findings Summary */}
                  <Typography
                    variant="subtitle2"
                    sx={{ mb: 2, fontWeight: 600 }}
                  >
                    Key Findings:
                  </Typography>
                  <List dense sx={{ mb: 2 }}>
                    {results.summary.map((point, index) => (
                      <ListItem key={index} sx={{ px: 0, py: 0.5 }}>
                        <ListItemText
                          primary={`• ${point}`}
                          primaryTypographyProps={{ variant: "body2" }}
                        />
                      </ListItem>
                    ))}
                  </List>

                  <Divider sx={{ my: 2 }} />

                  {/* Sources */}
                  <Typography
                    variant="subtitle2"
                    sx={{ mb: 2, fontWeight: 600 }}
                  >
                    Sources ({results.sources.length}):
                  </Typography>
                  <Box sx={{ maxHeight: 400, overflow: "auto" }}>
                    {results.sources.map((source, index) => (
                      <Paper
                        key={index}
                        variant="outlined"
                        sx={{ p: 2, mb: 2 }}
                      >
                        <Box sx={{ mb: 1 }}>
                          <Link
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            variant="subtitle2"
                            sx={{ fontWeight: 600, textDecoration: "none" }}
                          >
                            {source.title}
                          </Link>
                          <Typography
                            variant="caption"
                            display="block"
                            color="text.secondary"
                          >
                            {source.domain}
                          </Typography>
                        </Box>
                        <List dense>
                          {source.source_summary.map((point, pointIndex) => (
                            <ListItem key={pointIndex} sx={{ px: 0, py: 0.25 }}>
                              <ListItemText
                                primary={`• ${point}`}
                                primaryTypographyProps={{ variant: "body2" }}
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Paper>
                    ))}
                  </Box>
                </Box>
              ) : (
                <Box
                  sx={{
                    flexGrow: 1,
                    backgroundColor: "#f8f9fa",
                    borderRadius: 1,
                    p: 3,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    textAlign: "center",
                  }}
                >
                  <Box>
                    <Search
                      sx={{ fontSize: 48, color: "text.disabled", mb: 2 }}
                    />
                    <Typography
                      variant="body1"
                      color="text.secondary"
                      sx={{ mb: 1 }}
                    >
                      Enter document details and click "Research & Summarize"
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      The system will generate search queries, find relevant
                      government sources, and create a comprehensive summary.
                    </Typography>
                  </Box>
                </Box>
              )}
            </Paper>
          </Box>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
