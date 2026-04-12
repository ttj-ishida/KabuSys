# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要モジュールと実行手順、設定方法、ディレクトリ構成をまとめたものです。

※ 本 README はソースコードに含まれる docstring と実装に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / 研究 / 監視コンポーネント群を含む Python パッケージです。主要な機能は次の通りです。

- 注文作成・送信・状態管理（Execution Engine, OrderManager, Reconciler）
- リスク管理（RiskManager）とリスク監視（RiskMonitor）
- システム監視（CPU・メモリ・ディスク・プロセス・データ鮮度）
- 監視ログ永続化（SQLite: monitoring.db）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制限）
- 研究用ファクター計算（Momentum / Value / Volatility 等）と特徴量解析
- ニュース NLP（OpenAI）による銘柄別センチメントスコア化および市場レジーム判定
- Streamlit による監視ダッシュボード
- Paper Trading 用シミュレーション / レポート生成ツール

設計上の特徴：
- DuckDB を用いた時系列・財務データ集計（ローカルファイル）
- SQLite による監視・注文ログ（production / paper_trading は分離可能）
- 環境変数／.env による柔軟な設定読み込み（自動読み込み機能あり）

---

## 機能一覧（主要コンポーネント）

- 実行・復旧
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / paper_trading 切替対応）
  - Reconciler: 起動時の注文同期 / ポジション差分チェック
  - OrderManager / OrderRepository: 注文ライフサイクル管理・永続化

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL）
  - MonitoringEngine: System / Trade / Risk 各 Monitor を束ねる
  - SystemMonitor / TradeMonitor / RiskMonitor: 個別チェックと MonitoringDB への書き込み
  - KillSwitch: フラグファイルで ExecutionEngine 停止シグナルを発行
  - AlertManager: LINE Push による通知（クールダウン管理）
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- ポートフォリオ・サイズ計算（純粋関数）
  - select_candidates / calc_equal_weights / calc_score_weights
  - apply_sector_cap / calc_regime_multiplier
  - calc_position_sizes（単元・制約・スケールダウン処理を含む）

- 研究（Research）
  - calc_momentum / calc_volatility / calc_value（DuckDB 経由でのファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析ユーティリティ）

- AI（OpenAI）
  - news_nlp.score_news(): ニュース記事を LLM で集約し銘柄別スコアを ai_scores テーブルへ保存
  - regime_detector.score_regime(): ETF ma200 短期乖離＋マクロニュースで市場レジーム判定

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順（ローカル開発向け）

前提：
- Python 3.10 以上を推奨（型注釈に Path | None 等を使用）
- Git リポジトリのルートに配置して利用する想定

1. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（プロジェクト独自の requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil requests openai streamlit
   - （開発時は logger やテスト用の追加ライブラリをインストールしてください）

3. 環境変数設定
   - .env または .env.local に必要な環境変数を置くか、OS 環境変数として設定します。
   - 自動読み込み：プロジェクトルートに .env / .env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な必須変数（用途）：
     - JQUANTS_REFRESH_TOKEN — J-Quants API（finance data）
     - KABU_API_PASSWORD — kabuステーション API のパスワード
   - 任意 / 推奨：
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 起動環境（development | paper_trading | live） デフォルト: development
     - LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
     - PAPER_FILL_MODE — paper_trading のモック約定動作（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）

4. データディレクトリ作成
   - mkdir -p data

5. 初回起動前に DuckDB / SQLite に必要なテーブルを作る（実行スクリプトが自動で init する箇所が多い）
   - run_monitoring / run_execution 起動時に monitoring DB の初期化が行われます。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番または paper_trading 切替に応じて DB/ブローカーが変わります）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

- SystemMonitor（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に production sqlite_path（KABUSYS_ENV に依らず settings.sqlite_path）を参照します。

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit ダッシュボード起動（監視 DB を読み取り専用で表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 関連（プログラム的に呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # duckdb 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

注意:
- run_execution / run_monitoring はプロセス優先度を High に設定しようとします（psutil が必要）。権限不足で警告が出ることがありますが、続行されます。
- kill.flag（Settings.kill_flag_path）により ExecutionEngine を安全に停止できます。KillSwitch は drawdown やポジション上限で flag を書き込みます。

---

## 主要環境変数（まとめ）

- KABUSYS_ENV: 起動環境（development|paper_trading|live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants）
- KABU_API_PASSWORD: 必須（kabuステーション）
- OPENAI_API_KEY: OpenAI を使う場合必須
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill フラグファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py  — パッケージ初期化、バージョン等
  - config.py    — 環境変数 / .env 読み込み、Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py        — ニュース集約→OpenAIで銘柄別スコア化（ai_scores へ書込）
    - regime_detector.py — 市場レジーム判定（ETF ma200 + マクロニュース）

  - monitoring/
    - monitoring_db.py   — SQLite 用永続化層（テーブル作成・CRUD）
    - system_monitor.py   — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py    — 滞留注文・約定異常監視
    - risk_monitor.py     — ドローダウン / ポジション上限監視（RiskMonitor）
    - kill_switch.py      — kill.flag 書き込みロジック
    - alert_manager.py    — LINE への通知機能
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 株数決定・単元丸め・コストバッファ処理
    - risk_adjustment.py   — セクター制限・レジーム乗数

  - research/
    - factor_research.py   — Momentum / Value / Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ等

  - execution/
    - order_manager.py
    - reconciler.py
    - （その他、broker API / repository 等の実装ファイル）

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 追加メモ / 運用上の注意

- Paper trading は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- DuckDB への書き込み・executemany 周りはバージョン依存の挙動（空リスト禁止等）に注意して実装されています。
- AI (OpenAI) 呼び出しはリトライ・バックオフとレスポンスバリデーションを実装していますが、APIキーの管理・コストに注意してください。
- pid / kill.flag によるプロセスマネジメントは OS 権限やファイルパスのアクセス権に依存します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加してほしい実行例（具体的な .env.example、systemd 用 service ファイル例、docker-compose 設定など）があれば、使い方に沿って追記します。