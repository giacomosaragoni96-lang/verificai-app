-- Schema Training AI per VerificAI
-- Database Supabase tables per sistema silenzioso

-- Tabella per raccogliere feedback utente
CREATE TABLE IF NOT EXISTS ai_feedback (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    verifica_content TEXT NOT NULL,
    materia TEXT NOT NULL,
    livello TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('good', 'bad')),
    features JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella per pattern di training
CREATE TABLE IF NOT EXISTS training_patterns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('positive', 'negative')),
    features JSONB NOT NULL,
    confidence FLOAT DEFAULT 0.0 CHECK (confidence >= 0 AND confidence <= 1),
    materia TEXT,
    livello TEXT,
    usage_count INTEGER DEFAULT 0,
    effectiveness_score FLOAT DEFAULT 0.0 CHECK (effectiveness_score >= 0 AND effectiveness_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabella per metriche training
CREATE TABLE IF NOT EXISTS training_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    metric_type TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    materia TEXT,
    livello TEXT,
    date_recorded DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_ai_feedback_user_id ON ai_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_materia_livello ON ai_feedback(materia, livello);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_rating ON ai_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_created_at ON ai_feedback(created_at);

CREATE INDEX IF NOT EXISTS idx_training_patterns_type ON training_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_training_patterns_materia_livello ON training_patterns(materia, livello);
CREATE INDEX IF NOT EXISTS idx_training_patterns_effectiveness ON training_patterns(effectiveness_score DESC);

CREATE INDEX IF NOT EXISTS idx_training_metrics_type_date ON training_metrics(metric_type, date_recorded);

-- RLS (Row Level Security) policies
ALTER TABLE ai_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_metrics ENABLE ROW LEVEL SECURITY;

-- Policy: solo admin possono leggere/scrivere training data
CREATE POLICY IF NOT EXISTS "Admin full access ai_feedback" ON ai_feedback
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE auth.users.id = auth.uid() 
            AND auth.users.email IN ('giacomosaragoni96@gmail.com')
        )
    );

CREATE POLICY IF NOT EXISTS "Admin full access training_patterns" ON training_patterns
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE auth.users.id = auth.uid() 
            AND auth.users.email IN ('giacomosaragoni96@gmail.com')
        )
    );

CREATE POLICY IF NOT EXISTS "Admin full access training_metrics" ON training_metrics
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE auth.users.id = auth.uid() 
            AND auth.users.email IN ('giacomosaragoni96@gmail.com')
        )
    );
