# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
ここに含まれるモジュールは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助（ニュースセンチメント／レジーム判定）などの主要機能を提供します。

以下は本コードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要
KabuSys は日本株の自動売買を目的としたモジュール群です。主な役割は次のとおりです。

- 実行エンジン（ExecutionEngine）による発注管理とリスク管理
- 監視コンポーネント（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）による稼働監視とアラート
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- リサーチ（ファクター計算・IC、将来リターン計算）
- AI 層（ニュースセンチメント、レジーム判定）による外部情報の統合
- ユーティリティ群（プロセス優先度設定・DB マイグレーション等）
- ツール類（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

設計上のポイント：
- DuckDB を用いた時系列データやファクター計算
- SQLite を用いた監視ログ / 発注ログの永続化
- Paper Trading（検証用）は本番 DB と分離可能
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロセンチメント（オプション）
- 自動化実行時の停止用フラグや PID 管理をサポート

---

## 機能一覧
主な機能群と代表的なモジュール：

- 監視（monitoring）
  - SystemMonitor（システム資源・プロセス・データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（各 Monitor を束ねポーリング）
  - AlertManager（LINE へアラート送信）
  - KillSwitch（条件に応じて停止フラグを書き込み、ExecutionEngine を停止）
  - streamlit_dashboard（リアルタイム監視ダッシュボード）

- 実行（execution）
  - ExecutionEngine（発注セッションの実行）
  - OrderManager / OrderRepository（注文ライフサイクル管理・SQLite 永続化）
  - Reconciler（再起動時の注文/ポジション突合）

- ポートフォリオ（portfolio）
  - 候補選定 / 等重・スコア加重 / リスク制約（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（単元丸め、aggregate cap）

- リサーチ（research）
  - calc_momentum / calc_volatility / calc_value（DuckDB 上でのファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（特徴量解析ユーティリティ）

- AI（ai）
  - news_nlp.score_news（ニュース記事を LLM で評価して ai_scores に保存）
  - regime_detector.score_regime（ETF MA とマクロセンチメントからレジーム判定）

- ツール（tools）
  - paper_verification_report（Paper Trading DB を対象に PASS/FAIL レポート生成）

- ユーティリティ
  - process_priority（プロセス優先度 / CPU affinity 設定）
  - config（.env 自動読み込み / 設定ラッパー）
  - monitoring_db（監視用 SQLite スキーマの初期化と操作）

---

## セットアップ手順（ローカル開発・実行）
以下はローカル環境での簡単なセットアップ手順例です。

1. Python 環境
   - Python 3.9+ 推奨（ソースに依存する機能に合わせ適宜）
   - 仮想環境を作るのがおすすめ:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（代表的な依存）
   - pip install duckdb psutil requests openai streamlit
   - 開発時は必要に応じて extras を追加してください。

   （注）requirements.txt はこのリポジトリに含まれていないため、上記の主要パッケージを目安にインストールしてください。

3. プロジェクトルートに .env を配置（オプション）
   - config モジュールはプロジェクトルートの `.env` および `.env.local` を自動読み込みします（OS 環境変数が優先）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env の最低例）:
   ```
   KABUSYS_ENV=development           # development | paper_trading | live
   OPENAI_API_KEY=sk-xxx             # news_nlp/regime_detector 使用時に必要
   JQUANTS_REFRESH_TOKEN=...         # J-Quants API 用
   KABU_API_PASSWORD=...             # kabuステーション API 用
   LINE_CHANNEL_ACCESS_TOKEN=        # AlertManager が必要な場合
   LINE_USER_ID=
   LOG_LEVEL=INFO
   ```

4. DB ディレクトリ作成（初回）
   - data ディレクトリを作成しておくと便利:
     - mkdir -p data

---

## 使い方（代表的なコマンド）
※全て Python モジュール実行スタイルで説明します。

1. 監視ループの起動（Monitoring）
   - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒）。
   - 監視は常に Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します（KABUSYS_ENV に依存しない）。
   - 実行:
     - python -m kabusys.run_monitoring
   - 停止:
     - プロジェクトルートの `data/stop_requested.flag` を作成するとループ終了処理が走ります。

2. 実行エンジンの起動（Execution）
   - KABUSYS_ENV=`paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` を使って本番 DB と完全分離します。
   - 実行:
     - python -m kabusys.run_execution
   - 途中停止:
     - `data/stop_requested.flag` を作成するとエンジン停止処理が走ります。
   - 実行中は PID ファイル `data/execution.pid` （既定）を利用します。

3. Streamlit ダッシュボード（監視の可視化）
   - 起動例（既に監視 DB がある前提）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは read-only モードで SQLite を開きます。

4. Paper Trading 検証レポート
   - Paper Trading の SQLite を解析して検証レポートを標準出力に出すツール:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       - --from YYYY-MM-DD
       - --to YYYY-MM-DD
       - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数を上書き）

5. AI モジュールの呼び出し（プログラム的に）
   - ニュース NLP:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=None)  # api_key を指定しない場合は OPENAI_API_KEY を参照
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)

---

## 設定（主な環境変数）
config.Settings で扱われる主要設定項目（デフォルト含む）を抜粋します。

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- OPENAI_API_KEY: Optional（news_nlp / regime_detector で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — Monitoring は常にこれを使用
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定挙動（instant/partial/never/reject、デフォルト: instant）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等の監視関連フラグ

注意点:
- Settings はプロジェクトルートの `.env` / `.env.local` を自動で読みに行きます（OS 環境が優先）。
- `.env` の読み込みはプロジェクトルートを `.git` または `pyproject.toml` から検出して行われます。

---

## ディレクトリ構成（抜粋）
主要なソース構成（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込み
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py                   — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py            — 市場レジーム判定（ETF MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py              — SQLite スキーマ初期化および永続化ラッパー
    - system_monitor.py             — システム/データ鮮度監視
    - trade_monitor.py              — 注文滞留/約定異常監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — 停止フラグ書き込みユーティリティ
    - alert_manager.py              — LINE 通知
    - monitoring_engine.py          — 各 Monitor を束ねる
    - streamlit_dashboard.py        — Streamlit ダッシュボード

  - execution/
    - reconciler.py                 — 起動時リコンシリエーション
    - order_manager.py              — 発注管理
    - order_repository.py           — Orders DB（SQLite）アクセス（※ソースは一部）
    - ...（BrokerFactory 等のブローカー抽象）

  - portfolio/
    - portfolio_builder.py          — 候補選定・重み付け
    - position_sizing.py            — 株数決定・ラウンド
    - risk_adjustment.py            — セクター制約・レジーム乗数

  - research/
    - factor_research.py            — Momentum/Volatility/Value 計算（DuckDB）
    - feature_exploration.py        — 将来リターン / IC / 統計ユーティリティ

  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成

- data/  （ランタイムで生成されるファイル）
  - monitoring.db (SQLite デフォルト)
  - paper_trading.db (Paper Trading 用 SQLite デフォルト)
  - kabusys.duckdb (DuckDB デフォルト)
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 運用上の注意・補足
- Monitoring は常に Settings.sqlite_path（監視用 DB）を使用します。監視ログは環境に依存せず一元管理されます。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_trading_db を用いて本番 DB と分離します。
- stop フラグ / PID 管理:
  - 停止要求: data/stop_requested.flag を作ると run_* スクリプトが検知して終了します。
  - KillSwitch は条件を満たすと data/kill.flag に理由を書き込み、Execution 側で停止を検出できます。
- init_monitoring_db は既存 DB へカラム追加（マイグレーション的処理）を行います（冪等）。
- OpenAI 呼び出しを行う関数は API エラーに対しリトライ処理やフェイルセーフ（スコア 0.0 で続行）を備えていますが、API キーは必須です。
- 本リポジトリは本番での運用リスク（ブローカー API や資金管理）を伴います。実運用前にローカル検証やコードレビューを推奨します。

---

この README はコードベースから主要な情報を抜粋してまとめたものです。詳細な API 使用方法や ExecutionEngine の設定・拡張方法は各モジュールの docstring やソースを参照してください。必要であれば README に追記したい項目（例: 環境変数の完全一覧、実行例の詳細、CI / デプロイ手順）を教えてください。