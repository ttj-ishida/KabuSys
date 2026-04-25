# KabuSys — 日本株自動売買システム

この README はリポジトリ内のコードベースに基づいた簡易ドキュメントです。開発用・運用用の起動スクリプト、設定ウィザード、検証ツール、ポートフォリオ構築・リスク計算、リサーチ／AI モジュール、監視機能などを含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 重要な環境変数・ファイル
- 運用時の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買を前提としたソフトウェア群です。主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）による実注文／ペーパートレードの実行
- 監視コンポーネントによるシステム・取引・リスク監視と Kill Switch
- ポートフォリオ構築とポジションサイズ計算（戦略側の純関数群）
- DuckDB/SQLite を利用したデータ処理・保管
- ニュースを用いた NLP スコアリング（OpenAI）や市場レジーム判定
- 検証・ユーティリティスクリプト（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部：
- 本番・ペーパートレードの DB を明確に分離
- 監視は本番の monitoring DB を参照（環境に依らず本番 sqlite_path を使用する箇所あり）
- OpenAI 等外部 API 呼び出しは明示的にキーを渡す／環境変数で指定する
- ルックアヘッド（future data）防止を考慮した実装

---

## 機能一覧

- 設定関連
  - 対話式 .env 作成・更新ウィザード: python -m kabusys.config_setup
  - 起動前設定検証: python -m kabusys.validate_config (--strict オプションあり)
- 実行系
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、専用 DB に記録
    - 停止は data/stop_requested.flag / data/kill.flag / pid ファイルで制御
  - 監視ポーリングループ: src/kabusys/run_monitoring.py
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き（デフォルト 60 秒）
    - Monitoring は常に本番 sqlite_path を参照して初期化（意図的な設計）
- 監視（monitoring）
  - system_monitor: CPU/メモリ/ディスク、実行プロセスの有無、データ鮮度検査
  - trade_monitor: 取引ログの監視（滞留注文、異常約定など）※実装ファイル群あり
  - risk_monitor: ドローダウン・ポジション上限検知、ダッシュボード更新、リスクログ追記
  - kill_switch: 条件に応じた data/kill.flag 書き込み（ExecutionEngine 停止トリガ）
  - MonitoringDB: SQLite テーブル定義・読み書き（system_status, trade_logs, positions, risk_logs, dashboard）
  - MonitoringEngine: 上記を束ねるポーリング実行器
- ポートフォリオ構築（純関数）
  - 候補選定、等重/スコア重み付け、セクターキャップの適用、ポジションサイズ計算（単元株丸めや aggregate cap）
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）: DuckDB を用いた集計関数
  - 特徴量探索（将来リターン、IC 計算、統計要約）
- AI（OpenAI 依存）
  - news_nlp.score_news: ニュースを集約して LLM で銘柄ごとのセンチメントを生成し ai_scores に書き込む
  - regime_detector.score_regime: ETF の MA とマクロニュースを組み合わせて market_regime を判定・保存
  - 両方とも OPENAI_API_KEY が必要（引数で明示的に渡すことも可能）
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
    - 稼働率、約定率、送信率、レイテンシ等を計算して PASS/FAIL 判定

---

## セットアップ手順

前提: Python 3.10 以上（コードは | 型注釈等を使用）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限の依存例:
     - duckdb
     - psutil
     - openai (AI機能を使う場合)
     - PyYAML（validate_config の YAML パースに必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （リポジトリ内に requirements.txt がない場合は上記のように必要パッケージを個別インストールしてください）

4. 初期設定ファイル (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照する想定）
   - 自動ロード: コード実行時にプロジェクトルートの .env, .env.local を自動で読み込みます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

6. データディレクトリ準備（必要に応じて）
   - デフォルトでは data/ 以下に DB や PID/flag を配置します。適切な権限があることを確認してください。

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使い MockBrokerClient で発注をシミュレーション
    - 停止フラグ: data/stop_requested.flag / data/kill.flag を検出すると安全に停止します
    - PID ファイル: data/execution.pid を使用

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 設定:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して init します（設計上の注意点）
    - 停止フラグ: プロジェクトルート/data/stop_requested.flagを検出するとループ終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db もしくは環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連関数（プログラム内から使用）
  - kabusys.ai.score_news (DuckDB コネクション + target_date + api_key)
  - kabusys.ai.regime_detector.score_regime (DuckDB コネクション + target_date + api_key)
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。CLI エントリは本コードには直接含まれていません（呼び出しは Python から）。

---

## 重要な環境変数・ファイル（抜粋）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development

- DB 関連
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — 監視 DB（monitoring）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB

- API / 認証
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合）

- ログ
  - LOG_LEVEL（default: INFO）
  - LOG_DIR（default: logs/）
  - ログ出力は logs/<app_name>.log に日次ローテーションで保存（TimedRotatingFileHandler）、失敗時はコンソールのみ出力

- 監視 / 制御関連
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、"1" でクリア）

- その他
  - PAPER_FILL_MODE（paper_trading 時の MockBrokerClient の約定動作: instant | partial | never | reject）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にすると自動 .env ロードを無効化

フラグ/PID 等のファイル:
- data/stop_requested.flag : 停止要求（run_execution/run_monitoring が参照）
- data/kill.flag : Kill Switch（monitoring が書き込む）
- data/execution.pid : 実行エンジンの PID

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主要なモジュール・ファイル一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 取引監視（滞留注文等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねる実行器
    - alert_manager.py       — （アラート送信の管理、LINE など）（実装あり）
  - execution/
    - execution_engine.py    — 実行エンジン本体（起動・セッション管理）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC / forward returns / 統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - (その他) data/, logs/ 等の実行時生成物を想定

---

## 運用上の注意点 / トラブルシューティング

- .env は絶対にリポジトリにコミットしないこと（config_setup でも注意書きが出ます）。
- run_monitoring は監視用 DB（Settings.sqlite_path）を常に使用します。テスト用に監視 DB を差し替えたい場合は Settings を調整してください。
- paper_trading モードでは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に完全分離してログを保存します。本番 DB を上書きすることはありません。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソールのみになります（setup_logging の挙動）。
- OpenAI API を使う機能は API 呼び出し失敗に対してリトライやフォールバック（0.0 等）を行う実装が多く、API キー未設定時は例外となる関数もあります（明示的に api_key を渡すか OPENAI_API_KEY を設定してください）。
- psutil を用いたプロセス優先度／CPU affinity の設定は OS により動作が異なります。権限不足などで設定に失敗しても警告を出して続行します。
- validate_config で PyYAML がインストールされていない場合、config/*.yaml の内容検証はスキップされます。YAML 検証が必要な場合は PyYAML をインストールしてください。

---

もし README に追加してほしい具体的な情報（例: サンプル .env のテンプレート、実際の起動パラメータ、細かい API 仕様や DB スキーマの詳細）があれば、目的に合わせて追記します。