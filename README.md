# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ群・CLI スクリプト群）。  
この README はリポジトリ内の主要な機能と使い方、セットアップ手順、ディレクトリ構成の概略を日本語でまとめたものです。

注意: .env や API キー等の機密情報は絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python モジュール群です。主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（本番 / ペーパートレードの分離）
- 監視（Monitoring）: システム状態、注文滞留、ドローダウン等の定期チェックとログ保存
- ポートフォリオ構築（候補選定、重み計算、リスク調整、数量計算）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- AI を利用したニュース NLP（OpenAI を用いたセンチメント評価）と市場レジーム判定
- ユーティリティ（設定ローダー、プロセス優先度設定、DB 初期化など）
- 各種 CLI（.env ウィザード、設定検証、ペーパートレード検証レポート等）

コードベースは「データ保持（DuckDB / SQLite）」「実行ロジック」「監視ロジック」「リサーチ」「AI」などに分かれています。

---

## 機能一覧（主なコンポーネント）

- kabusys.config
  - .env 自動読み込み（プロジェクトルートが検出できる場合）
  - Settings クラスで環境変数を型付きにラップ
- kabusys.config_setup
  - .env を対話式に作成・更新するウィザード
- kabusys.validate_config
  - .env / config/*.yaml の整合性チェック CLI
- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading なら MockBroker を使用、Paper DB に分離）
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔指定可）
  - monitoring/:
    - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, MonitoringDB（SQLite ベースの永続層）
- ポートフォリオ
  - portfolio/ : 候補選定、重み、数量決定、セクター上限、レジーム乗数
- リサーチ
  - research/ : ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリー
- AI
  - ai/news_nlp.py: OpenAI を用いたニュースセンチメント（ai_scores への書き込み）
  - ai/regime_detector.py: ETF MA とマクロニュースの LLM センチメントを合成してレジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成

---

## 前提依存パッケージ

最低限必要なパッケージ（pip インストール例）:

- python 3.9+
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML（validate_config の config/*.yaml 内容検証に使用、無くても動作するが警告になる）

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン・ワークディレクトリへ移動
2. 仮想環境を作成し依存パッケージをインストール
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # Windows: .venv\Scripts\activate
     pip install -U pip
     pip install duckdb psutil openai PyYAML
     ```
3. .env の作成（対話式ウィザード推奨）
   - 実行:
     ```
     python -m kabusys.config_setup
     ```
   - 必須設定（主なもの）:
     - JQUANTS_REFRESH_TOKEN（J-Quants API トークン）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 注意: .env を絶対にリポジトリへコミットしないでください。

4. 設定検証
   - .env と config/*.yaml の基本チェック:
     ```
     python -m kabusys.validate_config
     ```
   - 警告もエラー扱いにする場合（CI 等）:
     ```
     python -m kabusys.validate_config --strict
     ```

5. DB 初期化
   - SQLite の監視 DB や DuckDB は、該当スクリプトが接続時に必要テーブルを自動作成します。特別な準備は不要です。
   - 監視 DB は init_monitoring_db() によりテーブルとマイグレーションが行われます。

---

## 使い方（主な CLI / 実行例）

- Execution（注文エンジン）を起動
  - ローカル開発 / ペーパートレード / 本番は KABUSYS_ENV により自動切替
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、デフォルトで data/paper_trading.db に書き込む（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID が書かれる（PID ファイルを検出して stale PID を扱うロジックあり）。

- System Monitor を起動（単体）
  - SystemMonitor のポーリングループを実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）。無効値や 0 以下の場合はデフォルトへフォールバック。
  - 監視は Settings.sqlite_path（本番 sqlite_path）を使用してログ保存します（KABUSYS_ENV に依らず本番 SQLite パスを使用する点に注意）。

- Paper Trading 検証レポート生成
  - 例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB は環境変数 PAPER_TRADING_SQLITE_PATH（または --db オプション）で指定可能。デフォルトは data/paper_trading.db。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要。関数はモジュールから呼び出す形です。
  - 例（Python REPL 等）:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")
    ```
  - OPENAI_API_KEY 未設定の場合、score_news / score_regime は ValueError を送出します。

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に .env / .env.local を自動読み込みします。
  - 自動ロードを無効にする場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- 停止（Kill Switch / stop フラグ）
  - 実行中の ExecutionEngine を停止したい場合、監視側・オペレーター側から data/kill.flag（Settings.kill_flag_path）を書き込むことで停止シグナルを送れます。
  - KillSwitch クラスは条件に応じて kill.flag を書き込み、ExecutionEngine はこのファイルを検知して停止します。
  - run_execution / run_monitoring 共に data/stop_requested.flag が存在する場合は起動やループを終了します。

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading の DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視 / 停止制御関連）
- PAPER_FILL_MODE（ペーパートレード時の約定挙動: instant / partial / never / reject）

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## よくあるトラブルとヒント

- validate_config が YAML をチェックできない:
  - PyYAML がインストールされていないと YAML の解析チェックはスキップされ警告が出ます。必要なら `pip install PyYAML`。
- AI 機能が OpenAI に接続できない:
  - OPENAI_API_KEY が設定されているか確認してください。API エラーはリトライロジックである程度保護されていますが、キーが無ければ例外になります。
- run_execution を起動しない / すぐ終了する:
  - 起動前に data/stop_requested.flag（または kill / stop フラグ）が存在していないか確認してください。
- モニタリングは常に本番 sqlite_path を参照:
  - run_monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（監視用 SQLite）を使用します。ペーパートレード用 DB は run_execution が切り替えて使います。

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys` 以下を抜粋した概観:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 読み込み、Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングスクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py            — SQLite 永続層（テーブル定義・CRUD）
    - system_monitor.py           — システム状態 / データ鮮度チェック
    - trade_monitor.py            — 注文滞留 / 約定異常チェック
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - kill_switch.py              — kill.flag 管理
    - alert_manager.py            — （アラート送信統括: 実装箇所）
    - monitoring_engine.py        — 各モニタの束ね（run_once / run ループ）
  - execution/
    - (注文関連のリポジトリ / マネージャ等: OrderRepository, OrderManager, ExecutionEngine 等)
  - portfolio/
    - portfolio_builder.py        — 候補選定 / 重み計算
    - position_sizing.py          — 株数計算 / 集約キャップ
    - risk_adjustment.py          — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py         — momentum / value / volatility 等
    - feature_exploration.py     — 将来リターン, IC, 統計
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI を使用）
    - regime_detector.py         — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 開発上の注意 / 設計ポイント（抜粋）

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行うため、CWD に依存しません。無効化も可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- Paper Trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- AI 呼び出しはリトライ・バックオフ・レスポンス検証を含む堅牢化が施されています。API キーが未設定の場合は呼び出し元で明示的なエラーとなります。
- Monitoring の DB マイグレーション（カラム追加）は init_monitoring_db() で自動的に行われ、冪等となるよう実装されています。
- プロセス優先度や CPU affinity の設定はプラットフォーム差分（Windows / POSIX）を吸収するユーティリティ関数を提供しています。権限不足時は警告ログを出して処理をスキップします。

---

必要であれば、README に以下の追記も可能です:
- 各モジュール（ExecutionEngine、OrderRepository など）のより詳細な API ドキュメント
- テストの実行方法
- CI / デプロイ手順
- サンプル .env.example の埋め込み

追記希望があればどの項目を詳しく書くか教えてください。