# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（ライブラリ兼実行スクリプト群）。

このリポジトリは、戦略の研究（ファクター計算・特徴量探索）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視機構、Paper Trading の検証・レポート、そして一部 AI（ニュースの NLP 判定 / 市場レジーム判定）を含むコンポーネントで構成されています。

- パッケージ名: `kabusys`
- バージョン: 0.1.0（`src/kabusys/__init__.py`）

以下はプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するためのモジュール群です。主な目的は以下:

- DuckDB ベースの価格・ファイナンスデータを使ったファクター計算・研究
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制約）
- 実際の発注エンジン（ExecutionEngine）とリスク管理（RiskManager）
- 監視（MonitoringEngine/SystemMonitor/RiskMonitor/TradeMonitor）と Kill Switch（停止フラグ）
- Paper Trading の検証とレポート生成
- ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI API を利用）

設計方針として、実行系と研究系を分離（DB の分離、paper_trading モードなど）、ルックアヘッドバイアス回避、フェイルセーフ（API失敗時のフォールバック）等を意識しています。

---

## 主な機能一覧

- 設定管理
  - `.env` 自動ロード（`.env` / `.env.local`）、Settings クラス（`kabusys.config.Settings`）
  - 対話式 .env 作成ウィザード（`kabusys.config_setup`）
  - 起動前設定検証 CLI（`kabusys.validate_config`）

- 実行・監視スクリプト
  - ExecutionEngine 起動スクリプト: `kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、本番 DB と分離して `data/paper_trading.db` に記録
  - Monitoring 起動スクリプト: `kabusys.run_monitoring`
    - 環境にかかわらず監視は本番監視 DB を使用（`SQLITE_PATH`）

- 監視コンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - Kill Switch（`data/kill.flag`）: 指定条件で書き込まれ、ExecutionEngine を停止させる仕組み
  - 監視ログ永続化（SQLite）: `monitoring_db.py`

- ポートフォリオ構築
  - 候補選定、重み計算、セクター上限適用、ポジションサイズ計算

- 研究（research）
  - ファクター計算（Momentum/Volatility/Value）
  - 将来リターン / IC 計算 / 統計サマリ

- AI（OpenAI）
  - ニュース NLP による銘柄ごとのセンチメント（`kabusys.ai.news_nlp.score_news`）
  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - OpenAI API を用いるため `OPENAI_API_KEY` が必要

- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 必要要件（主な依存関係）

- Python 3.10 以上（PEP 604 union types 等を使用）
- 外部ライブラリ:
  - duckdb
  - psutil
  - openai
  - PyYAML（`validate_config` の YAML 検証に任意で使用）
- その他: sqlite3 は標準ライブラリに含まれます

インストールはプロジェクトに requirements ファイルがあればそれを使用してください。例:

pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. `.env` の作成（対話式ウィザード推奨）:

   実行して `.env` を生成 / 更新できます:

   python -m kabusys.config_setup

   対話ウィザードが起動し、J-Quants トークン、kabuステーションパスワード、DB パス等を入力できます。

   または、手動で `.env` を作成する場合の最小例:

   ```
   # .env の例（最低限必要なもの）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_api_password_here
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   ```

4. 設定検証（任意だが推奨）:

   python -m kabusys.validate_config

   --strict オプションを付けると警告も失敗扱いになります。

5. 初回 DB 準備
   - 実行スクリプトが起動時に監視用 SQLite テーブルを自動作成します（`init_monitoring_db`）。
   - DuckDB 用のスキーマ/データは外部処理（データ収集パイプライン）で準備してください。

6. ログディレクトリ
   - デフォルトで `logs/` に日次ローテーションログが出力されます。環境変数 `LOG_DIR` で変更可能。

---

## 使い方

ここでは主要なスクリプトの起動方法と注意点を示します。

- ExecutionEngine を起動する

  環境変数で `KABUSYS_ENV` を設定して実行してください。

  - 本番（実際の発注を行う）:

    KABUSYS_ENV=live python -m kabusys.run_execution

  - Paper Trading（MockBroker を使い DB を `data/paper_trading.db` に隔離）:

    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  - 開発 / テスト（発注抑止）:

    KABUSYS_ENV=development python -m kabusys.run_execution

  実行時:

  - プロセス優先度が自動で "high" に設定されます（`psutil` を使用）。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します（停止フラグ機構）。
  - PID ファイルはデフォルト `data/execution.pid` に書き込まれます（Settings.pid_file_path で変更可能）。

- Monitoring を起動する

  python -m kabusys.run_monitoring

  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒単位）。
  - 監視は Settings.sqlite_path（`SQLITE_PATH`）の DB を利用してログを記録します（環境にかかわらず本番パスを参照する設計）。
  - 停止は `data/stop_requested.flag` を作成することで、ループが検知して終了します。
  - 監視中に kill 条件を満たすと `data/kill.flag` が作成され、ExecutionEngine の停止トリガーになります（Kill Switch）。

- Paper Trading 検証レポート

  python -m kabusys.tools.paper_verification_report
  期間指定や DB パス指定が可能:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

  デフォルトの DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。

- .env ウィザード・検証

  - ウィザード:

    python -m kabusys.config_setup

  - 検証:

    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- AI（ニュース NLP / レジーム検出）

  - OpenAI API キー (`OPENAI_API_KEY`) が必要です（引数で渡すことも可）。
  - news_nlp と regime_detector は DuckDB の `raw_news`, `news_symbols`, `prices_daily` 等のテーブルを参照します。適切なデータが必要です。
  - 例: `kabusys.ai.score_news(conn, target_date, api_key=...)` / `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)`

---

## 停止・Kill Switch・フラグ類

- 停止フラグ: `data/stop_requested.flag`
  - 起動スクリプト（monitoring / execution）はこのファイルが存在するとループを抜けて終了します。外部の運用ツールが停止要求をセットするのに使います。

- Kill Switch: `data/kill.flag`
  - 監視側が致命的リスク（ドローダウン超過など）を検出した際に `kill.flag` を書き込み、ExecutionEngine に停止通知を行うための仕組みです。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアしますが、本番では `0`（クリアしない）を推奨します。

- PID ファイル: `data/execution.pid`（デフォルト）
  - ExecutionEngine が PID を書き込みます。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LOG_LEVEL, LOG_DIR: ログ出力レベル・ディレクトリ
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の Fill 動作（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアするか（"0"/"1"）

※より詳細な設定は `kabusys.config.Settings` を参照してください。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 配下の主要なファイル・ディレクトリです（この README 作成時点の抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py 等)
  - execution/               — 発注関連（Engine, BrokerFactory, OrderManager, RiskManager 等）
  - portfolio/               — portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/                — factor_research.py, feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリの完全なツリーはローカルで `tree src/kabusys` 等で確認してください）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。自動クリアは危険です。
- .env は機密情報を含むため Git にコミットしないでください（`config_setup` のヘッダにも注意書きあり）。
- OpenAI を使う機能は API コストとレイテンシが発生します。失敗時はフォールバックがある設計ですが、運用ポリシーを事前に定めてください。
- ログは日次ローテートで 30 日保存されます（`logs/<app_name>.log`）。ログディレクトリが作れない場合はコンソール出力のみになります。
- Paper Trading と本番 DB は分離されています（`PAPER_TRADING_SQLITE_PATH` を使用）。Paper トレードの検証時に本番データを汚染しないよう注意してください。

---

## さらに詳しく / 開発者向け

- ファクター計算やリサーチ機能は DuckDB 接続を直接受け取る純粋関数群です。ユニットテストが書きやすく設計されています。
- モジュール間は可能な限り副作用を避けるように分割されています（例: News NLP と Regime Detector で API 呼び出し関数を別実装にするなど）。
- マイグレーションや互換性を部分的にサポート（`monitoring_db.init_monitoring_db` は既存カラムの追加を行う）しています。

---

問題や改善案、ドキュメント追加の要望があれば教えてください。README に追加したい運用手順やサンプルコマンドがあれば追記します。