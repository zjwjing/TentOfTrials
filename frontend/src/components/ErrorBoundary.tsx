import React from 'react';

interface ErrorBoundaryFallbackProps {
  error: Error | null;
  resetError: () => void;
}

export interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode | ((props: ErrorBoundaryFallbackProps) => React.ReactNode);
  name?: string;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  resetKeys?: unknown[];
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

const initialState: ErrorBoundaryState = {
  hasError: false,
  error: null,
  errorInfo: null,
};

const haveResetKeysChanged = (prevResetKeys: unknown[] = [], nextResetKeys: unknown[] = []) => {
  if (prevResetKeys.length !== nextResetKeys.length) {
    return true;
  }

  return prevResetKeys.some((key, index) => !Object.is(key, nextResetKeys[index]));
};

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = initialState;

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    this.props.onError?.(error, errorInfo);

    if (import.meta.env.DEV) {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    if (
      this.state.hasError &&
      haveResetKeysChanged(prevProps.resetKeys, this.props.resetKeys)
    ) {
      this.resetErrorBoundary();
    }
  }

  resetErrorBoundary = () => {
    this.setState(initialState);
  };

  renderFallback() {
    const { fallback, name = 'this page' } = this.props;
    const { error, errorInfo } = this.state;

    if (typeof fallback === 'function') {
      return fallback({ error, resetError: this.resetErrorBoundary });
    }

    if (fallback) {
      return fallback;
    }

    return (
      <div
        role="alert"
        aria-live="assertive"
        style={{
          margin: '24px auto',
          maxWidth: 720,
          padding: 24,
          border: '1px solid rgba(239, 68, 68, 0.35)',
          borderRadius: 12,
          background: 'rgba(127, 29, 29, 0.12)',
          color: '#f8fafc',
          boxShadow: '0 12px 30px rgba(15, 23, 42, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
          <div
            aria-hidden="true"
            style={{
              width: 40,
              height: 40,
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              flexShrink: 0,
              background: 'rgba(239, 68, 68, 0.18)',
              color: '#fca5a5',
              fontSize: 22,
            }}
          >
            ⚠
          </div>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: '0 0 8px', fontSize: 20, color: '#fecaca' }}>
              Something went wrong
            </h2>
            <p style={{ margin: '0 0 16px', color: '#cbd5e1', lineHeight: 1.5 }}>
              We could not render {name}. You can try again or reload the page.
            </p>

            {error?.message && (
              <pre
                style={{
                  margin: '0 0 16px',
                  padding: 12,
                  overflowX: 'auto',
                  borderRadius: 8,
                  background: 'rgba(15, 23, 42, 0.65)',
                  color: '#fca5a5',
                  fontSize: 12,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {error.message}
              </pre>
            )}

            {import.meta.env.DEV && errorInfo?.componentStack && (
              <details style={{ marginBottom: 16, color: '#94a3b8' }}>
                <summary style={{ cursor: 'pointer' }}>Component stack</summary>
                <pre
                  style={{
                    marginTop: 8,
                    padding: 12,
                    overflowX: 'auto',
                    borderRadius: 8,
                    background: 'rgba(15, 23, 42, 0.65)',
                    fontSize: 12,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={this.resetErrorBoundary}
                style={{
                  padding: '10px 16px',
                  border: 'none',
                  borderRadius: 8,
                  background: '#ef4444',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Try again
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                style={{
                  padding: '10px 16px',
                  border: '1px solid #475569',
                  borderRadius: 8,
                  background: 'transparent',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Reload page
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  render() {
    if (this.state.hasError) {
      return this.renderFallback();
    }

    return this.props.children;
  }
}

export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>,
) {
  const WrappedComponent: React.FC<P> = (props) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name || 'Component'})`;

  return WrappedComponent;
}

export default ErrorBoundary;
