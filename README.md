# KabuSys

日本株自動売買システムのコアライブラリ群。シグナル生成、ポートフォリオ構築、発注エンジン、監視・アラート、研究用ツール群などを含むモジュール化された設計です。

以下はコードベースに基づく README です。

## プロジェクト概要
KabuSys は日本株の自動売買ワークフローを支えるライブラリ群です。主な役割は以下です。

- 価格・財務データを用いたファクター計算（research）
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- 発注管理・Execution Engine（paper/live 両対応）
- 実行・監視のためのユーティリティ（ロギング、プロセス優先度設定、Kill Switch）
- Paper Trading 検証レポート生成ツール
- ニュースNLP / レジーム判定などの AI 補助機能（OpenAI 経由）

設計方針として、DB（DuckDB / SQLite）への読み書きや LLM 呼び出しは明示的に分離され、ルックアヘッドバイアス防止などの安全対策が組み込まれています。

---

## 主な機能一覧
- research:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- portfolio:
  - 候補選定、等配分・スコア加重配分
  - セクター上限の適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- execution:
  - ExecutionEngine 起動スクリプト（paper_trading モードは MockBroker）
  - 発注／注文管理／リスク管理モジュール（ExecutionEngine 周辺）
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を永続化
  - Kill Switch（条件により ExecutionEngine を停止するための flag 書込み）
- ai:
  - ニュース NLP によるセンチメントスコアリング（OpenAI 利用）
  - 市場レジーム判定（ma200 + マクロセンチメントの合成）
- tools:
  - Paper Trading 検証レポート（paper_verification_report）
- utils:
  - 統一ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - 環境変数ロード・設定ウィザード・検証ツール

---

## 必要条件（依存関係）
最低限想定される依存ライブラリ（実際の requirements.txt に従ってください）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML 検証を行う場合）

また、システムでのファイル書込み権限やネットワークアクセス（kabu API / OpenAI）が必要です。

---

## セットアップ手順（ローカルでの初期セットアップ）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合は上記の主要パッケージを個別にインストールしてください）

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   ウィザードは .env を生成・更新します。作成後に必須値（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を確認してください。

4. 設定検証
   - python -m kabusys.validate_config
   必須環境変数や config/*.yaml（存在すれば）の構文等をチェックします。
   --strict を付けると警告も失敗扱いになります。

5. データディレクトリの作成（必要に応じて）
   - data/（SQLite や PID・flag ファイル用）
   - logs/（ログ格納用。logging_setup が自動で作成しますが、権限を確認してください）

---

## 主要な環境変数（抜粋）
（デフォルト値は config.Settings のプロパティに記載されているものに従います）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject。デフォルト: instant）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

Kill / stop フラグ関連:
- data/stop_requested.flag: run_execution / run_monitoring が存在を検知してループを終了するための停止フラグ（外部からの停止要求）
- data/kill.flag: KillSwitch が条件を満たしたときに書き込むフラグ。主に ExecutionEngine 停止用（Settings.kill_flag_path で上書き可能）

---

## 使い方（主要コマンド）
- .env を生成・編集（対話式）
  - python -m kabusys.config_setup

- 設定の静的検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番／ペーパー自動切替）
  - python -m kabusys.run_execution
  - 実行前に KABUSYS_ENV を設定（例: KABUSYS_ENV=paper_trading）すると、paper_trading モードで MockBrokerClient を使用し data/paper_trading.db に記録します。
  - 実行中に data/stop_requested.flag を作成すると優雅に停止します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - Monitoring は .env の KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視 DB を更新します。
  - run_monitoring も data/stop_requested.flag を検知して停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼ぶか、用途に合わせてスクリプト化してください。
  - OpenAI API キー（OPENAI_API_KEY）が必要です。API レスポンスの不安定さに対するリトライが実装されています。

---

## ログ
- ログは console (stdout) とファイル（日次ローテート）に出力されます。
- デフォルトのログディレクトリは logs/。app 名に応じて logs/execution.log, logs/monitoring.log などが作成されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging から統一的に行われます。

---

## 停止・Kill Switch の仕組み
- stop_requested.flag:
  - 長時間実行スクリプト（run_execution/run_monitoring）は data/stop_requested.flag の有無を定期チェックし、存在する場合は安全に終了します。
  - オペレータが外部からプロセスを止めたい場合にこのファイルを作成してください。

- kill.flag (Kill Switch):
  - 監視ロジック（KillSwitch）がリスク閾値を超えると Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込んで ExecutionEngine に停止を要求します。
  - KillSwitch は冪等に動作し、既存の kill.flag がある場合は再書き込みを行いません。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールと用途の一覧です（抜粋）。

- kabusys/
  - __init__.py — パッケージ定義 / バージョン
  - config.py — 環境変数・設定管理（.env 自動ロード・検証関数）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメントスコア付与
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 発注ログ等の監視（ファイル内に同名モジュールあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（flag 書込み）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート管理：LINE 送信等の実装がここにある想定）
  - execution/
    - execution_engine.py — 実行エンジン（セッション管理）
    - broker_factory.py — ブローカークライアント作成（Mock / 実ブローカ）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周りのコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラ系の計算
    - feature_exploration.py — IC やファクター探索ユーティリティ
  - data/ (想定)
    - pipeline.py 等（DuckDB / prices_daily などのデータ取得パイプライン）
  - utils/
    - logging_setup.py — 共通のロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
    - __init__.py

（上記はコードベースから抽出した主要ファイル。実運用では追加のスクリプト・設定ファイルが存在する可能性があります。）

---

## 開発上の注意点 / 運用メモ
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）運用時は LINE アラート等の通知設定を必ず確認してください（validate_config が警告を出します）。
- ExecutionEngine は paper_trading モード時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離します。テストは必ず paper_trading モードで行ってください。
- OpenAI API 呼び出しはレート制限や一時的なエラーを考慮してリトライが実装されていますが、利用コスト・レート制限に注意してください。
- ログは stdout とファイルに出力されます。システム起動処理で logging_setup.setup_logging を呼び出してから処理を行ってください（起動スクリプトは既に行っています）。

---

この README はコードベースの主要な機能と運用に関する要点をまとめたものです。より詳細な設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）や運用手順が別にある場合はそちらを参照してください。追加で README に含めたい項目（例: CI / デプロイ手順、具体的な設定例、FAQ など）があれば教えてください。