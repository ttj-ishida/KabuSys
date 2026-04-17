# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ / 実行モジュール群）。  
この README はリポジトリ内の主要モジュールから自動生成的にまとめたもので、プロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインを構成するモジュール群です。  
主な目的は以下：

- データパイプライン（DuckDB ベース）を利用したファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine による発注処理（本番 / ペーパートレードの切り替え）
- 監視（System / Trade / Risk）と Kill Switch（安全停止機構）
- ニュース NLP を用いたセンチメント評価（OpenAI 利用）
- 各種ユーティリティ / レポート生成（ペーパートレード検証レポート等）

設計方針としては「可能な限り副作用を避ける」「本番 DB とペーパートレード DB を明確に分離」「外部 API 呼び出しは注意深く（フェイルセーフ / リトライ）」などが採用されています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（.env の対話生成）: python -m kabusys.config_setup
- 設定検証 CLI（env / config/*.yaml のチェック）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading では MockBroker を使用し、ペーパートレード専用 DB（data/paper_trading.db）に記録
- 監視ループ起動スクリプト（SystemMonitor ポーリング）: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視サブシステム:
  - SystemMonitor: CPU / メモリ / ディスク / Execution プロセスの存否 / データ鮮度 を監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視（kill.flag のトリガー）
  - MonitoringDB: SQLite に監視ログを永続化
  - MonitoringEngine: 上記モニターを束ねてポーリング・LINE 通知などを行う
- AI 関連:
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出・保存
  - regime_detector: ma200 とマクロセンチメントを合成して市場レジーム判定
- 研究・リサーチ:
  - factor_research, feature_exploration: DuckDB を用いたファクター計算・IC 等の評価
- ポートフォリオ構築:
  - 候補選定、等配分/スコア加重、セクター制限、ポジションサイズ計算（単元株丸め・制約考慮）
- ツール:
  - paper_verification_report: ペーパートレード履歴から検証レポートを生成（稼働率 / 注文成功率 / レイテンシ 等）

---

## 依存関係（主なもの）

最低限想定される依存パッケージ（開発環境に合わせて適宜インストールしてください）:

- Python 3.10+
- duckdb
- psutil
- openai
- requests
- PyYAML（設定検証で YAML 検証を行う場合）
- （そのほか execution モジュールや broker client 実装に応じたライブラリ）

例（pip）:
pip install duckdb psutil openai requests pyyaml

※ requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリに移動
2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests pyyaml
4. .env を用意
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）
5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます
6. DB / data ディレクトリ
   - デフォルトでは data/ 以下にファイルを作成します（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定

---

## 環境変数（主要なもの）

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（よく使う）:
- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading: 発注は MockBroker に切り替わり data/paper_trading.db を使用
  - live: 本番モード（注意: 実際に発注されます）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動 ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" で有効、既定は "0"）

ファイルパス（デフォルト）:
- data/execution.pid — ExecutionEngine が書く PID ファイル（監視でプロセス検出）
- data/stop_requested.flag — run_execution / run_monitoring が監視する「停止要求フラグ」
- data/kill.flag — KillSwitch が書き込む停止フラグ（Execution 停止トリガー）

---

## よく使うコマンド / 使い方

1. .env 作成（対話式）:
   - python -m kabusys.config_setup

2. 設定検証:
   - python -m kabusys.validate_config
   - 厳格チェック: python -m kabusys.validate_config --strict

3. 実行エンジン起動（本番 / 開発 / ペーパートレード）:
   - 本番想定（環境変数を .env に設定してから）:
     - python -m kabusys.run_execution
   - ペーパートレード（明示）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - ペーパートレード時は PAPER_TRADING_SQLITE_PATH に記録され、本番 DB と分離されます

4. 監視ループ起動（SystemMonitor）:
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更する場合:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5. ペーパートレード検証レポート:
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定（デフォルトは env or data/paper_trading.db）:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6. Kill Switch / 停止フラグ:
   - 管理者が kill.flag を作成すると ExecutionEngine は安全停止します（KillSwitch による書き込みも同様）。
   - フラグの手動クリア:
     - rm data/kill.flag
   - run scripts は data/stop_requested.flag を存在チェックしてシャットダウンします。停止要求を出したい場合はこのファイルを作成します（または管理用スクリプトを使う）。

7. AI 関連（ニューススコア / レジーム判定）
   - news_nlp の呼び出しは DuckDB 接続と API キーを渡して行います（ライブラリ API を参照）。
   - OPENAI_API_KEY を .env に設定しておくとモジュール内で自動取得します。
   - 実行例（ライブラリ呼び出し）:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- 実行時に psutil を使ってプロセス優先度を変更しようとします。権限が不足すると警告が出ますが動作は継続します。
- .env や API キーは絶対にリポジトリにコミットしないでください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル・モジュールの一覧（抜粋）です。

- kabusys/
  - __init__.py (バージョン定義)
  - config.py
    - 環境変数と .env 自動ロードロジック、Settings クラス
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - execution/                  (発注周りのモジュール群。Broker クライアント等）
  - data/                       (実行時に生成する DB / PID / フラグファイルなど)
  - config/                     (config YAML テンプレート：system_config.yaml 等)

（注）上記はリポジトリ内の主要モジュールを抜粋した一覧です。実際のファイル構成はリポジトリの tree を参照してください。

---

## 運用上の注意

- KABUSYS_ENV=live のときは十分に設定を確認してください（validate_config の警告を特に確認）。
- Kill Switch（data/kill.flag）や stop_requested.flag の扱いは慎重に。KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動クリアされますが、本番では推奨されません。
- OpenAI API 呼び出しはレート制限、ネットワークエラー、API エラーに対してリトライやフォールバック（0.0）で安全に設計されていますが、API キーの漏洩やコストには注意してください。
- DuckDB / SQLite のパスは .env で調整可能。運用では永続化パス（SSD など）を確保することを推奨します。
- psutil によるプロセス優先度設定はプラットフォーム権限に依存します。失敗しても警告を出すのみで継続します。

---

この README はコードベースのコメント・ドキュメントを元に要点をまとめたものです。各モジュールの詳細な使用法や API（関数シグネチャ、例）は該当ソースファイルの docstring を参照してください。必要であれば各モジュールごとの Usage サンプルやデプロイ手順を別ドキュメントとして展開できます。