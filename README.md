# KabuSys

日本株自動売買システムのライブラリ群（ライブラリ/モジュール群）。ポートフォリオ構築、ポジションサイズ計算、ファクター計算、ニュース NLP によるセンチメント評価、実行エンジン／監視機構などの主要コンポーネントを含みます。

---

## 概要

KabuSys は、以下の目的を持つモジュール化された Python コードベースです。

- DuckDB / SQLite を用いたリサーチ・データ処理
- ファクター計算 / 特徴量解析（モメンタム、ボラティリティ、バリュー等）
- ポートフォリオ構築（候補選定、重み付け、セクター制限、レジーム調整）
- ポジションサイズ計算（リスクベース、等配分、スコア加重）
- ニュース記事の LLM（OpenAI）によるセンチメント評価および市場レジーム判定
- 実行（ExecutionEngine）・発注管理・リコンシリエーション
- 監視（MonitoringEngine）・アラート（LINE push）・ダッシュボード（Streamlit）

設計方針として、運用フェーズでの安全性（クラッシュ耐性、冪等性、ルックアヘッド防止）を重視しています。

---

## 主な機能一覧

- 環境設定の自動読み込み（.env / .env.local、オーバーライド挙動）
- Portfolio:
  - 候補選定（score 降順 + tie-breaker）
  - 重み計算（等金額 / スコア加重）
  - セクター集中制限適用
  - レジームに応じた投資乗数
  - ポジションサイズ計算（risk_based / equal / score）
- Research:
  - モメンタム、ボラティリティ、バリューファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI:
  - ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄毎にセンチメントを算出（ai_scores へ書き込み）
  - マクロニュースと ETF (1321) MA200乖離を統合して市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ / フェイルセーフロジックを内包
- Execution:
  - OrderManager / OrderRepository による注文ライフサイクル管理（クラッシュ耐性を考慮した永続化）
  - Reconciler による再起動時の復旧・突合
  - ExecutionEngine によるシグナル処理・WebSocket ドレインループ・kill switch 機構
- Monitoring:
  - SQLite による監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - 各種モニタ（SystemMonitor / TradeMonitor / RiskMonitor）、アラート送信（LINE）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

前提
- Python 3.10 以上（typing における |, 型注釈を想定）
- DuckDB, OpenAI SDK, requests, psutil, streamlit 等の依存ライブラリが必要

1. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb openai requests psutil streamlit
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。読み込み優先順位は:
   - OS 環境変数
   - .env.local（既存の OS 環境変数を保護して上書き）
   - .env（上書きしない）

   自動ロードを無効化する場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

   代表的な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
   - DUCKDB_PATH: DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: Paper Trading の fill 動作（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development | paper_trading | live
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. 監視 DB の初期化（監視機能を使う場合）
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（代表的な例）

以下はライブラリを直接利用する簡単なサンプルです。

- DuckDB からファクター計算（モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  result = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュースセンチメントのスコア付け（OpenAI API キー必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 市場レジーム判定（OpenAI を使う）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- Portfolio（候補選定 → 重み付け → ポジションサイズ計算）
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [
      {"code": "1234", "signal_rank": 1, "score": 2.5},
      {"code": "5678", "signal_rank": 2, "score": 1.2},
  ]
  candidates = select_candidates(buy_signals, max_positions=5)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(
      weights=weights,
      candidates=candidates,
      portfolio_value=10_000_000,
      available_cash=1_000_000,
      current_positions={},
      open_prices={"1234": 1200.0, "5678": 800.0},
  )
  ```

- 監視ダッシュボード（Streamlit）
  起動例（read-only）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- 環境変数の明示的読み取り（settings）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live
  ```

---

## 主要モジュール（簡単な説明）

- kabusys.config: 環境変数読み込み・設定取得（Settings クラス）
- kabusys.portfolio: portfolio_builder, position_sizing, risk_adjustment（選定・重み・サイズ計算）
- kabusys.research: factor_research, feature_exploration（ファクター計算・IC）
- kabusys.ai: news_nlp（ニュースセンチメント）, regime_detector（市場レジーム判定）
- kabusys.execution: execution_engine, order_manager, reconciler, broker_api（発注周り）
- kabusys.monitoring: monitoring_db, system_monitor, trade_monitor, risk_monitor, alert_manager, streamlit_dashboard（監視・アラート）

---

## ディレクトリ構成

（抜粋／代表例）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - execution/
      - broker_api.py
      - execution_engine.py
      - order_manager.py
      - reconciler.py
      - (order_repository.py, order_record.py, risk_manager.py 等 想定)
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - alert_manager.py
      - kill_switch.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - research/, data/, etc.（プロジェクトにより追加）
- pyproject.toml / setup.cfg / .gitignore など（プロジェクトルート）

---

## 注意点・運用時のヒント

- Python バージョン: 3.10 以上を推奨（型注釈で | を使用）
- 環境変数は OS 環境変数が優先されます。自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に探索します。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。API のレート制限やコストに注意してください。
- 実行時の kill.flag（Settings.kill_flag_path）を使った外部停止シグナルをサポートしています。運用前にフラグパスやクリア設定（KILL_FLAG_CLEAR_ON_START）を確認してください。
- DuckDB・SQLite ファイルのバックアップを定期的に行ってください。
- 実運用では Paper Trading モード（KABUSYS_ENV=paper_trading）の利用や PAPER_FILL_MODE の設定を検討してください。

---

もし README に追加したい具体的な項目（例: CI / テスト実行方法、開発ルール、デプロイ手順）があれば教えてください。必要に応じてサンプルの docker-compose / systemd ユニット例やより詳細な起動手順も作成できます。