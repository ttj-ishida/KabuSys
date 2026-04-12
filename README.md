# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ツール群です。本リポジトリは以下の主要コンポーネントを含みます：

- Execution（発注エンジン・リコンシリエーション・リスク管理）
- Monitoring（システム状態・注文監視・アラート・ダッシュボード）
- Portfolio（銘柄選定・配分・ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI（ニュース NLP によるセンチメント集約 / レジーム判定）
- Tools（Paper Trading の検証レポート生成等）

以下は開発者向けの導入・使い方ドキュメントです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（起動コマンド）
- 環境変数（主要な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買のためのライブラリ兼実行ツール群です。  
設計方針の要点：

- DuckDB / SQLite を用いたデータ処理・ログ保存
- Execution と Monitoring を分離し、監視側から Execution を安全に停止できる kill flag（data/kill.flag）を採用
- Paper Trading（模擬発注）を本番 DB と完全分離して検証可能
- ニュースセンチメント解析や市場レジーム判定に LLM（OpenAI）を利用する拡張機能あり
- 研究用モジュール（ファクター計算・IC 計算など）を提供

---

## 主な機能一覧

- Execution
  - OrderManager, ExecutionEngine（発注管理・リスク管理）
  - Reconciler（起動時の自動復旧・ブローカー照合）
  - BrokerFactory により実環境 / Paper Trading 切り替え

- Monitoring
  - SystemMonitor（CPU/メモリ/Disk・プロセス・データ鮮度）
  - TradeMonitor（滞留注文／約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件達成で Execution 停止フラグを作成）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視データ可視化）
  - monitoring DB 初期化 / 永続化モジュール

- Portfolio
  - 候補選定、等配分 / スコア配分、ポジションサイズ計算、セクターキャップ、レジーム乗数

- Research
  - ファクター計算（Momentum / Value / Volatility）
  - 前方リターン計算、IC（スピアマン）計算、統計サマリー

- AI
  - news_nlp.score_news: ニュース記事を LLM へ送り銘柄別センチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: MA とマクロセンチメントを合成して市場レジームを判定・書き込み

- Tools
  - paper_verification_report: Paper Trading 用の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈や union 型（|）が使われているため推奨）
- SQLite（標準ライブラリ）
- データフォルダ（デフォルトで data/ 以下を使用）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd ...

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例（pip）:
     - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt が無い場合は上記を手動でインストールしてください。

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data

5. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くことで自動ロードされます（既存 OS 環境変数を上書きしない）。
   - 主要な環境変数の例は下記「環境変数」セクションを参照。

注意:
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

---

## 使い方（起動・各種コマンド）

※ すべてプロジェクトルートで実行することを想定します。モジュールとして実行可能です。

1. ExecutionEngine を起動（本番または paper_trading 切替）
   - 本番（デフォルト KABUSYS_ENV=development / live）
     - python -m kabusys.run_execution
   - Paper Trading（MockBroker を使用し data/paper_trading.db に記録）
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   実行時は process priority が high に設定され、SQLite と DuckDB に接続します。
   Paper Trading の場合は `paper_fill_mode`（PAPER_FILL_MODE）などで挙動を調整できます。

2. Monitoring（ポーリングループ）を起動
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
   - python -m kabusys.run_monitoring

   注意: Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を参照します（監視ログは一元管理）。

3. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - オプション `--db` で別 DB を指定できます（読み取り専用で開きます）。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連（プログラムから呼び出し）
   - ニューススコア集計:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")

   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")

6. 監視の停止（Kill Switch）
   - RiskMonitor や TradeMonitor の判定で KillSwitch がトリガーされると `data/kill.flag` に停止理由が書き込まれます。ExecutionEngine はこのフラグを検出して安全に停止できます。
   - 起動時に `kill_flag_clear_on_start` が有効なら自動的にクリアされます（Settings.kill_flag_clear_on_start）。

---

## 主要な環境変数（Settings で読み込むもの）

必須・推奨の主なキー（.env 例）:

- JQUANTS_REFRESH_TOKEN ・・・ J-Quants API トークン（必須）
- KABU_API_PASSWORD      ・・・ kabuステーション API パスワード（必須）
- OPENAI_API_KEY         ・・・ OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV            ・・・ 実行環境（development | paper_trading | live） デフォルト: development
- LOG_LEVEL              ・・・ ログレベル（DEBUG, INFO, ...）
- DUCKDB_PATH            ・・・ DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            ・・・ 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH・・・ Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE        ・・・ paper_trading 時の模擬約定モード（instant|partial|never|reject）
- PID_FILE_PATH          ・・・ ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH         ・・・ kill.flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL  ・・・ run_monitoring のポーリング間隔（秒）※任意の環境変数
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID ・・・ LINE 通知に使用（未設定時は送信されない）

簡単な .env 例:
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=xxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

注意: Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みます。OS 環境変数を優先します。

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイル / ディレクトリ概観（抜粋）：

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                  — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py           — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py             — monitoring SQLite のスキーマ / CRUD
    - system_monitor.py            — システム状態監視
    - trade_monitor.py             — 注文監視
    - risk_monitor.py              — ドローダウン / ポジション監視
    - kill_switch.py               — kill.flag 管理
    - alert_manager.py             — LINE 通知
    - monitoring_engine.py         — 各 Monitor を束ねる
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - reconciler.py                — 起動時リコンシリエーション
    - order_manager.py             — 注文ステートマシン API
    - order_repository.py (参照)
    - ...（ブローカー API, order_record 等）※本コードベースの一部
  - portfolio/
    - portfolio_builder.py         — 候補選定・スコアソート
    - position_sizing.py           — 株数計算・投資配分
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py           — ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py       — IC / forward returns / summary
    - __init__.py
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (想定／出力先)
    - kabusys.duckdb (デフォルト)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)

---

## 注記 / 運用上のポイント

- Monitoring は監視情報を永続化するために SQLite（デフォルト: data/monitoring.db）を使用します。init_monitoring_db() は冪等にテーブルを作成・必要なマイグレーションを行います。
- run_execution は KABUSYS_ENV=paper_trading 指定時に MockBroker を使用し、Paper Trading 用の別 DB（data/paper_trading.db）に記録します。本番 DB と完全に分離される設計です。
- AI 機能を利用する場合は OPENAI_API_KEY の設定が必要です。API 呼び出しはリトライ・フォールバック（失敗時にスコアを 0.0 等）を備えていますが、API キーが未設定だと一部関数は ValueError を送出します。
- PID ファイルと kill.flag により Execution を外部から安全に停止できます。Monitoring が stale PID を検出した場合には適切にログ / risk_logs に記録されます。
- 設計は「読み込み側で Look-ahead バイアスを避ける」方針を採用しており、AI / リサーチの各モジュールは target_date の扱いに注意して実装されています。

---

必要に応じて README をプロジェクト固有の運用フローや CI、テストの実行方法で拡張できます。追加でドキュメント化したい箇所（例: Broker 実装仕様・DB スキーマ定義・運用 runbook）があれば教えてください。