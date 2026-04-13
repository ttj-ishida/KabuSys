# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成などをまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。以下の主要機能を持ち、検証用の Paper Trading モードや監視・アラート・リコンシリエーション機能を備えています。

- 発注エンジン（ExecutionEngine / OrderManager / RiskManager）
- ブローカー抽象化（BrokerClientFactory を通じて Mock / 実ブローカーを切替）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ログ・ダッシュボード用の SQLite（monitoring.db）と分析用 DuckDB（kabusys.duckdb）
- Paper Trading 検証レポート生成ツール
- ニュース NLP によるセンチメント評価 & 市場レジーム判定（OpenAI を利用）
- Streamlit による監視ダッシュボード

設計上の特徴：
- 環境変数 / .env による設定管理（自動ロードをサポート）
- 本番と Paper Trading の DB 分離（Paper は data/paper_trading.db 等）
- フェイルセーフ（API失敗時のフォールバックや冪等な DB 書き込み）

---

## 機能一覧（抜粋）

- Execution
  - Order 作成 / 送信 / 同期（OrderManager, Reconciler）
  - RiskManager による発注制御
  - 起動時のリコンシリエーションで発注・ポジション差分を修復

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - AlertManager: LINE Push による通知（クールダウンあり）
  - KillSwitch: 条件に応じてフラグファイルを書き ExecutionEngine 停止指示

- Research / Data
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算、統計サマリー
  - DuckDB を使った高速集計

- AI
  - news_nlp.score_news: OpenAI を用いたニュースごとのセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロ記事センチメントを合成し日次レジーム判定

- ツール
  - streamlit ダッシュボード（監視用）
  - tools.paper_verification_report: Paper Trading 検証レポート生成

---

## 必要条件

- Python 3.10 以上（型アノテーションでの | 型記法などを利用）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)
  - その他（必要に応じて pip でインストール）

例（仮）:
pip install duckdb psutil requests streamlit openai

注意: 実環境では requirements.txt / pyproject.toml を参照してください（本リポジトリ側で提供している場合）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux / macOS)
   - .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt がない場合は上記の必須パッケージを個別にインストール）

4. 環境変数の設定
   - プロジェクトルートに `.env` および必要なら `.env.local` を作成できます。
   - 自動ロードはデフォルトで有効。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所がある場合）
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 利用時）
     - PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方

以下では主な起動コマンドと用途を示します。各スクリプトは `src/kabusys/...` 内のモジュールを参照します。プロジェクトルートまたはパッケージインストール後に実行してください。

1. ExecutionEngine（発注エンジン）起動
   - 本番 / Paper を切替えるには `KABUSYS_ENV` を設定します。
   - 例（paper_trading）:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - paper_trading の場合、MockBrokerClient が使用され、DB は `PAPER_TRADING_SQLITE_PATH`（既定: data/paper_trading.db）に記録されます。
   - 例（live）:
     KABUSYS_ENV=live python -m kabusys.run_execution

2. Monitoring（監視）起動
   - ポーリングループで SystemMonitor を起動します。`MONITOR_POLL_INTERVAL` で間隔を秒単位で上書き可能。
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は常に本番の sqlite_path（Settings.sqlite_path）を参照します（環境に依らず）。

3. Streamlit ダッシュボード（監視 UI）
   - 起動:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視用 DB を読み取り専用で開きます（monitoring エンジンが書き込む DB）。

4. Paper Trading 検証レポート
   - 使い方:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   - レポートは system_status, trade_logs, risk_logs 等から基準値を比較して PASS/FAIL を出力します。

5. AI 関連
   - ニュースセンチメント:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
       - DuckDB 接続と target_date（日付）を渡して ai_scores テーブルへ書き込みます。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- 実行前に `data` ディレクトリや DB の権限・パスを確認してください。
- ExecutionEngine は起動時に PID ファイルを書き込みます。プロセス管理に注意してください（PID ファイル破損時は SystemMonitor が検出・削除します）。
- KillSwitch が条件を満たすと `KILL_FLAG_PATH` にフラグを書き、ExecutionEngine 側で停止処理を期待する設計です。

---

## 主要モジュール（説明）

- kabusys.config
  - .env 自動ロード（.env, .env.local）と設定取得用 Settings クラス
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- kabusys.execution
  - run_execution.py: ExecutionEngine 起動スクリプト
  - OrderManager / Reconciler / order_repository など発注・同期ロジック

- kabusys.monitoring
  - run_monitoring.py: SystemMonitor のポーリング起動スクリプト
  - MonitoringDB: SQLite テーブル初期化・ログ永続化（init_monitoring_db）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch
  - streamlit_dashboard.py: 監視用 UI

- kabusys.research
  - factor_research, feature_exploration: DuckDB を用いたファクター計算・解析

- kabusys.ai
  - news_nlp: OpenAI を使ったニュースセンチメント → ai_scores へ書き込み
  - regime_detector: ETF MA とマクロセンチメント合成による市場レジーム判定

- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定・ウェイト算出・セクター制限・ポジションサイズ計算

- kabusys.utils
  - process_priority: プロセス優先度・CPU affinity を OS に依らず設定するユーティリティ

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（news / regime 機能）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PID_FILE_PATH: 実行 PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag（default: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

各プロパティの検証は `kabusys.config.Settings` で行われます（不正値は ValueError）。

---

## ディレクトリ構成（抜粋）

（src 配下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository 等)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (実行時に作成されることが多い)
      - kabusys.duckdb
      - monitoring.db
      - paper_trading.db

---

## 運用上の注意 / トラブルシューティング

- PID / kill.flag
  - ExecutionEngine は起動時に PID ファイルを書きます。PID ファイルが不正だったり既にある場合、SystemMonitor が検出して削除するロジックがあります。
  - KillSwitch により `data/kill.flag` が書かれると ExecutionEngine に停止指示が出る想定です。手動クリアは `Settings.kill_flag_clear_on_start` 等の設定や `KillSwitch.clear()` を使用してください。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルとインデックスを作成します。既存 DB に不足カラムがあれば簡単な ALTER を行う処理も含みます。

- OpenAI 呼び出し
  - rate limit / ネットワーク障害 / 5xx は指数バックオフでリトライする設計です。
  - API キーが未設定の場合、score_news / score_regime は ValueError を出します（呼び出し側で捕捉してください）。

- 権限
  - psutil によるプロセス優先度設定や CPU affinity は権限が必要な場合があります（AccessDenied が出ると警告を出してスキップします）。

---

## 開発メモ

- 設定の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から .env を読み込みます。パッケージ配布後もカレントワークディレクトリに依存しないよう実装されています。
- 各コンポーネントは可能な限り副作用を避ける純粋関数（portfolio / research 等）と、DB 等を扱う永続化層（monitoring_db, order_repository）に分離しています。
- テスト時は環境変数や API 呼び出しをモックすることを想定した設計になっています（例: news_nlp._call_openai_api の差し替えなど）。

---

この README はリポジトリ内の主要ファイル（src/kabusys 以下）を参照してまとめたものです。追加の使い方や設定は実際の運用ドキュメント・ .env.example を参照してください。必要であれば各コマンドの systemd / supervisor 用のユニット例や docker-compose 例も作成できます。