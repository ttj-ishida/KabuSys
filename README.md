# KabuSys

日本株向けの自動売買システム用ライブラリ / 実行スクリプト群です。  
このリポジトリには、実運用向けの ExecutionEngine、監視（Monitoring）周り、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュース解析、各種ユーティリティが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定（.env）ウィザード
  - 設定検証
  - 実行エンジン起動（Execution）
  - 監視ループ起動（Monitoring）
  - Paper Trading 検証レポート生成
  - AI 機能（ニューススコアリング / レジーム判定）
  - 停止・Kill Switch
- ディレクトリ構成（主なファイル説明）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤の一部を実装したモジュール群です。主に以下を提供します。

- ExecutionEngine（発注・リスク管理・オーダー管理）
- Monitoring（システム健全性、注文ログ、リスク監視、Kill Switch）
- Portfolio construction（銘柄選定・重み付け・株数算出）
- Research（ファクター計算、IC 計算、将来リターン）
- AI モジュール（ニュースのセンチメントスコアリング、マクロセンチメントによるレジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定読み込みウィザード・検証）

設計方針の一部：
- 本番とペーパートレードを明確に分離（paper_trading 環境では mock broker と専用 DB を使用）
- DuckDB を分析用に利用、SQLite を監視/オーダーログ保存に利用
- 外部 API 呼び出し（OpenAI など）はオプションで、失敗時はフェイルセーフにする設計

---

## 機能一覧

主な機能（抜粋）：

- 実行・発注
  - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient）
  - ExecutionEngine によるセッション実行、リスク制御、注文履歴（SQLite）保存

- 監視
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor：注文の滞留・約定異常検出（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch：条件トリガで data/kill.flag を書き込み ExecutionEngine 停止を誘発
  - MonitoringEngine：上記モニタをまとめてポーリング・アラート通知

- ポートフォリオ構築
  - 銘柄選定、等重／スコア加重、リスクベース位置サイズ算出、セクターキャップ、レジーム乗数

- リサーチ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ

- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントスコアを ai_scores に書き込み
  - regime_detector: ETF（例: 1321）の MA200 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定

- ツール
  - config_setup: .env を対話式に生成/更新
  - validate_config: .env と config/*.yaml の事前検証
  - tools.paper_verification_report: Paper Trading の検証レポート生成

- ユーティリティ
  - logging_setup: 統一ロギング（stdout + 日次ローテーション）
  - process_priority: プラットフォーム差分を吸収してプロセス優先度や CPU affinity を設定
  - config: .env 自動読み込み・Settings クラス経由で設定取得

---

## セットアップ手順

前提
- Python 3.9+（ソースは型注釈、標準ライブラリの機能を使用）
- システムに duckdb と psutil がインストール可能であること

基本手順（例）:

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - optional: pip install pyyaml （validate_config で YAML 検証を行う場合）

   （リポジトリに requirements.txt がない場合は上記を個別にインストールしてください。）

3. プロジェクトルートに .env を用意
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動: .env.example（存在する場合）を参考に .env を作成する

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL として扱う場合: python -m kabusys.validate_config --strict

5. データディレクトリ作成（アプリ起動時に自動作成されることもありますが念のため）
   - mkdir -p data logs

注意:
- OpenAI を利用する機能を使う場合は環境変数 OPENAI_API_KEY を設定してください。
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings にて必須に指定）。
- デフォルトの DB パスなどは Settings クラス内で定義されています（以下参照）。

主要な環境変数（主なもの）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB デフォルト）
- PID_FILE_PATH: data/execution.pid（実行エンジン PID ファイル）
- KILL_FLAG_PATH: data/kill.flag（Kill Switch フラグ）
- KILL_FLAG_CLEAR_ON_START: 0 or 1（1 の場合起動時に kill.flag を自動クリア）
- LOG_LEVEL: INFO（デフォルト）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

---

## 使い方

以下に主な CLI/スクリプトの使い方を示します。

### 環境設定（.env）ウィザード
対話式で .env を作成／更新します。

- 実行:
  - python -m kabusys.config_setup
- オプション:
  - --env-file <path> : 保存先を指定

ウィザードは機密値をマスクして表示し、完了後 .env を生成します。
注意: .env を絶対にリポジトリにコミットしないでください。

### 設定検証
作成した設定と config/*.yaml の整合性をチェックします。

- 実行:
  - python -m kabusys.validate_config
- 厳格モード（警告も失敗にする）:
  - python -m kabusys.validate_config --strict

### 実行エンジン起動（Execution）
ExecutionEngine を起動します。KABUSYS_ENV により paper_trading（MockBroker）と live（実ブローカー）を切り替えます。

- 実行:
  - python -m kabusys.run_execution

挙動:
- 起動直後にプロセス優先度を "high" に設定し、SQLite/ DuckDB に接続します。
- paper_trading 環境では専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します（本番 DB と分離）。
- data/stop_requested.flag があると起動をスキップまたは停止します。
- ExecutionEngine は data/execution.pid に PID を書く設計です。

### 監視ループ起動（Monitoring）
監視ループを起動して SystemMonitor 等をポーリングします。

- 実行:
  - python -m kabusys.run_monitoring

挙動:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60）。
- Monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。
- data/stop_requested.flag が存在するとループを抜けて終了します。
- system/process 停止検出、データ鮮度チェック、risk モニタの結果に応じて KillSwitch へつなぐことができます。

### Paper Trading 検証レポート生成
ペーパートレード用 SQLite のログからレポートを生成します。

- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

出力: 稼働率、注文成功率、送信率、P95 レイテンシ等を表示し PASS/FAIL を判定します。

### AI 機能（ニューススコアリング / レジーム判定）
OpenAI を利用する機能群（news_nlp.score_news, ai.regime_detector.score_regime）は OPENAI_API_KEY を必要とします。

- ニューススコアリング（例）:
  - Python API 呼び出し: kabusys.ai.score_news(conn, target_date, api_key=None)
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照

- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- API 呼び出しはリトライ処理を行いますが、キー未設定の場合は例外になります。
- レスポンスのバリデーション・スコアのクリップ等の安全策を講じています。

### 停止・Kill Switch
- run_execution / run_monitoring では data/stop_requested.flag を確認して停止します。
  - 停止指示を出すにはプロセス外からファイルを作成してください（例: touch data/stop_requested.flag）
- KillSwitch（監視による停止）は data/kill.flag を作成して ExecutionEngine に停止指示を出します。
  - 実行環境開始時に KILL_FLAG_CLEAR_ON_START=1 にすると自動で kill.flag をクリアできますが、本番では 0 を推奨します。
- kill.flag は存在すると ExecutionEngine 側で停止処理のトリガになります（仕組みは ExecutionEngine の実装に依存）。

---

## ディレクトリ構成（主なファイルの説明）

（リポジトリの src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード（.env / .env.local）と Settings クラス
  - config_setup.py
    - .env を対話式に生成・更新するウィザード
  - validate_config.py
    - 起動前に設定と config/*.yaml を検証する CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（メインエントリ）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（メインエントリ）
  - tools/
    - paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプト
  - utils/
    - logging_setup.py
      - ルートロガーの設定（stdout + 日次ファイルローテーション）
    - process_priority.py
      - Windows / POSIX を吸収してプロセス優先度 / CPU affinity を設定
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数計算・制約・ロット丸め
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py: raw_news → OpenAI で銘柄ごとのセンチメント算出、ai_scores へ書き込み
    - regime_detector.py: MA200 とマクロニュースを合成して市場レジーム判定
  - monitoring/
    - monitoring_db.py: SQLite スキーマの初期化・永続化操作（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度チェック
    - trade_monitor.py: （注文関連監視 — 実装参照）
    - risk_monitor.py: ドローダウン & ポジション上限監視、dashboard 更新
    - kill_switch.py: kill.flag の生成・評価
    - monitoring_engine.py: 各モニタをまとめて定期実行するエンジン
  - execution/
    - （ExecutionEngine, OrderManager, Reconciler, RiskManager, BrokerFactory 等 — 実行ロジック）
  - data/ (実行時に利用する各種ファイル)
    - monitoring.db（SQLite）
    - paper_trading.db（ペーパートレード用 SQLite）
    - kabusys.duckdb（DuckDB）
    - execution.pid, stop_requested.flag, kill.flag など
  - logs/ （ログファイル出力先、デフォルト）

---

## 注意点 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトで 0 を推奨します。
- paper_trading 環境は本番データと完全に分離されるように設計されています。発注は MockBroker を使用し、別 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
- OpenAI の呼び出しはトークン消費・レート制限・コストに注意してください。AI 機能は必須ではありません。
- ログは stdout と logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ書き込み権限を確認してください。
- SQLite / DuckDB のパスやログレベルは .env で簡単に上書き可能です。

---

もし README に追加したい項目（例: サンプル .env、より詳細な ExecutionEngine の使い方、単体テストの実行方法など）があれば教えてください。必要に応じて追記します。