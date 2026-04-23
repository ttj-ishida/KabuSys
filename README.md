# KabuSys

日本株向け自動売買システムのコアライブラリ群。  
このリポジトリには、環境設定ウィザード・設定検証・モニタリング・実行エンジン起動・研究用ファクター計算・AI を使ったニュース解析などのユーティリティが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、以下の主要機能を持つ自動売買システムの基盤モジュール群です。

- 環境設定のウィザード (.env 生成)
- 設定検証ツール（.env や config/*.yaml の事前チェック）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）
- Monitoring（システム状態・注文・リスク監視）と Kill Switch
- ポートフォリオ構築（候補選択、重み算出、ポジションサイズ算出）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算等）
- AI モジュール（ニュースのセンチメント解析、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、DB マイグレーション等）
- ペーパートレード検証レポート生成スクリプト

設計方針のポイント:
- 本番とペーパートレードの DB を分離（ペーパートレード用 DB: data/paper_trading.db）
- ルックアヘッドバイアスを避ける設計（日時の扱いに注意）
- フェイルセーフ（API 失敗時のフォールバック、部分失敗で全体を破壊しない書き込み等）

---

## 機能一覧

主な機能（抜粋）:

- 環境設定
  - config_setup.py: 対話的に .env を生成 / 更新
  - validate_config.py: 起動前に設定と必須環境変数・ファイルの検証

- 実行 / モニタリング
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により挙動を切替）
    - paper_trading の場合は MockBroker を使用し、専用 SQLite に記録
  - run_monitoring.py: SystemMonitor ポーリングループを実行
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
  - monitoring パッケージ:
    - system_monitor: システム資源・データ鮮度監視
    - trade_monitor: 注文滞留や約定異常の検出（モジュール参照）
    - risk_monitor: ドローダウン・ポジション上限監視
    - kill_switch: 条件に基づく kill.flag 書き込み（ExecutionEngine 停止）
    - monitoring_db: SQLite テーブル作成・永続化 API

- ポートフォリオ構築
  - portfolio パッケージ: 候補選定、重み算出、セクター制限、ポジションサイズ計算

- 研究・分析
  - research パッケージ: ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリ

- AI（OpenAI）
  - ai.news_nlp: ニュース記事から銘柄別センチメントを生成して ai_scores テーブルへ書き込み
  - ai.regime_detector: ETF とマクロニュースで市場レジーム（bull/neutral/bear）を判定

- ツール
  - tools.paper_verification_report: ペーパートレード DB から PASS/FAIL レポートを生成

- ユーティリティ
  - utils.logging_setup: 統一的なロギング（コンソール + 日次ローテーション）
  - utils.process_priority: プラットフォーム差を吸収した優先度設定（psutil 使用）
  - config.py: 環境変数読み込み / Settings クラス

---

## セットアップ手順

前提:
- Python 3.9+（typing 機能を利用）
- pip 等で必要パッケージをインストール

推奨インストール例:
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証（validate_config）でオプション: pip install PyYAML

3. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（後述の環境変数一覧を参照）

4. 設定検証（任意・推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 下に DB や PID/フラグファイルが置かれます。ログは logs/。

注意:
- 自動で .env を読み込む処理は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途）。

---

## 環境変数（代表的なもの）

主要な環境変数とデフォルト:

- 必須（少なくとも設定しておく）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境関連
  - KABUSYS_ENV: execution モード ("development" | "paper_trading" | "live") — デフォルト: development
  - LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL") — デフォルト: INFO
  - LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）

- データベース
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードの約定モード ("instant" | "partial" | "never" | "reject") — デフォルト: instant

- モニタリング / 制御
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"0" or "1"、デフォルト 0）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

- OpenAI
  - OPENAI_API_KEY: AI モジュールで使用する API キー

その他は config_setup のウィザードが説明する通りです。.env には機密値は含まれるため、絶対にコミットしないでください。

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env を生成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いになります

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB に記録し MockBroker を使用

- Monitoring を起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で変更できます

- Kill / Stop の仕組み
  - run_execution/run_monitoring はプロジェクトの data/stop_requested.flag を監視しています（プロジェクトルートの data ディレクトリに stop_requested.flag を置くとループが終了します）
  - kill_switch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine へ停止要求を送ります
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では危険なので注意）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）

- AI モジュールの実行（プログラムから呼び出す）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を環境変数で指定するか、明示的に api_key を渡します

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 # Settings / .env 自動読み込み
  - config_setup.py           # 対話式 .env ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # 注文監視（参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # アラート送信（参照）
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
    - logging_setup.py
    - process_priority.py

- data/                       # 実行時に使用する（DB / PID / flags）
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                       # ログ出力（デフォルト）

※ 実際のリポジトリにはさらに細かいモジュールや補助ファイルが含まれます。上は主要なエントリポイントとサブパッケージの一覧です。

---

## 実用上の注意・運用メモ

- データベースの初期化:
  - run_execution/run_monitoring は起動時に monitoring DB のテーブル作成（init_monitoring_db）を行います（冪等操作）。手動での初期化は不要です。

- ログ:
  - utils.logging_setup.setup_logging を各起動スクリプトで最初に呼び出しています。LOG_DIR を設定するとログ出力先を変更できます。

- プロセス優先度:
  - 実行スクリプトは起動時に set_process_priority("high") を呼び出します（psutil による設定）。権限不足で設定できない場合は警告が出ますが処理は継続します。

- ペーパートレード:
  - KABUSYS_ENV=paper_trading の際は paper_sqlite_path に保存され、本番 DB と分離されます。PAPER_FILL_MODE で約定シミュレーションの挙動を制御できます。

- AI 呼び出し:
  - OpenAI API を呼ぶ部分はリトライ/バックオフ/入力サイズ制限/レスポンス検証などを行う設計です。API キーは環境変数 OPENAI_API_KEY で指定してください。

- Kill Switch:
  - kill.flag は一度書き込まれると ExecutionEngine の停止トリガーになります（明示的にクリアしない限り残る）。本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨します。

---

必要であれば、README に以下を追記できます:
- 各モジュール（ExecutionEngine、OrderManager、BrokerClient 等）の詳細設計ドキュメント要約
- データベーススキーマの詳細
- 具体的なデプロイ / systemd / supervisor 用の起動例
- 単体テスト・統合テストの手順

追加で欲しい内容があれば教えてください（例: systemd ユニットファイル例、サンプル .env テンプレート、よくあるトラブルシュートなど）。