# KabuSys

日本株向け自動売買システムのコアライブラリ（README）

本ドキュメントはリポジトリ内のコードベースに基づく簡易 README です。起動スクリプト、設定ウィザード、検証ツール、監視／実行エンジン、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤を想定した Python モジュール群です。主な役割は以下の通りです。

- ExecutionEngine（発注エンジン）: 実際の発注（またはペーパートレード）を管理
- Monitoring（監視）: システム状態、注文状態、リスク（ドローダウン／ポジション数）を定期チェック
- Portfolio（銘柄選定・配分）: 候補選定、重み付け、株数計算などの純関数群
- Research（ファクター計算・特徴量解析）: DuckDB を用いたファクター計算・IC 計算など
- AI モジュール: ニュースのセンチメント解析（OpenAI）や市場レジーム判定
- 設定管理ツール: .env ウィザード、設定検証 CLI
- ユーティリティ: ロギング設定、プロセス優先度設定 等
- ツール: Paper Trading 検証レポート等

設計方針として、本番データベースとペーパートレードデータベースを分離、外部 API 呼び出しは明示的に管理、ルックアヘッドバイアスを避ける実装などが採用されています。

---

## 機能一覧（主なもの）

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live の挙動を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定関連
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI
  - Settings クラス: 環境変数の集中管理（Settings オブジェクト）
- 監視関連
  - MonitoringDB: SQLite を用いた監視ログレイヤ
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine: 監視ロジックとポーリング統合
  - KillSwitch: 条件に応じて data/kill.flag を書き込む仕組み
- ポートフォリオ構築
  - 銘柄選定（select_candidates）
  - 重み計算（等配分・スコア加重）
  - ポジションサイズ計算（リスクベース、制約・単元丸め・aggregate cap）
  - セクターキャップ・レジーム乗数
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM に渡し銘柄ごとにセンチメントを算出 → ai_scores へ書込
  - regime_detector: ma200 乖離 + マクロニュースセンチメントを合成して市場レジームを判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL レポート生成
- ユーティリティ
  - ロギングセットアップ（コンソール + 日次ローテーションファイルロギング）
  - プロセス優先度 / CPU affinity 設定（psutil 利用）

---

## 前提・依存関係

推奨 Python バージョン: 3.10 以上（型ヒントの union operator 等を使用）

主な外部パッケージ（一例）:
- duckdb
- psutil
- openai
- PyYAML（validate_config で YAML 検証を有効にする場合）
（SQLite は標準ライブラリに含まれます）

インストール例:
pip install duckdb psutil openai PyYAML

注意: 実際の requirements.txt は本リポジトリに含まれていないため、プロジェクト固有のバージョン管理は別途行ってください。

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. data, logs ディレクトリの作成（自動作成は試みるが手動で用意しておくと安全）
   - mkdir -p data logs
5. 環境変数設定
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または .env を手動作成（.env は絶対に Git 管理へコミットしないでください）
     例（最低限の必須項目）:
       JQUANTS_REFRESH_TOKEN=your_jquants_token_here
       KABU_API_PASSWORD=your_kabu_password_here
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
6. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 本番前は --strict を付けることを検討: python -m kabusys.validate_config --strict

追加（OpenAI を使う場合）:
- 環境変数 OPENAI_API_KEY に API キーを設定するか、AI 関数呼び出し時に引数でキーを渡してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading: MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB とは分離）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）（デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant|partial|never|reject）
- LOG_LEVEL / LOG_DIR
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=クリア, 0=クリアしない）

---

## 使い方（よく使うコマンド）

- .env の初期作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番確認: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログを保持します。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止方法:
- run_execution / run_monitoring はプロジェクトルート下の data/stop_requested.flag を検出すると停止します（ファイルを作成して停止を伝える仕組み）。
- KillSwitch は条件が満たされると data/kill.flag を書き込み、ExecutionEngine に停止を促す（設定により起動時に自動クリア可能）。

ログ:
- デフォルトで stdout にログを出力し、logs/<app_name>.log に日次ローテートで保存します（LOG_DIR 環境変数で変更可）。

---

## ディレクトリ構成

リポジトリの主要なファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py  (実装想定)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - data/ (ランタイムで作成される想定)
    - logs/ (ランタイムで作成される想定)

（注）一部ファイルは抜粋表示です。実プロジェクトではさらにモジュールやサンプル設定ファイルが存在する可能性があります。

---

## 実装上の注意点（開発者向け）

- Settings は環境変数を直接参照するため、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを無効化できます。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- AI モジュールは OpenAI のレスポンス依存のため、API エラー時はフォールバック（スコア 0.0）やリトライを行う設計になっています。テスト時は API 呼び出し箇所を差し替えてください（モジュール内に差し替え可能な関数が設計されています）。
- ロギングは setup_logging() を介して統一的に設定してください。ログディレクトリ作成失敗時はコンソールのみで動作します。
- MonitoringDB はスキーマのマイグレーション処理（カラム追加）を含んでいます。既存 DB を使用する場合は注意してください。
- ポートフォリオ／ポジション計算は純粋関数群として実装されているため、単体テストしやすい構成です。

---

## よくある質問（短く）

Q: 本番とペーパートレードの DB は分離されていますか？  
A: はい。KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

Q: 監視ループの間隔は変更できますか？  
A: はい。MONITOR_POLL_INTERVAL 環境変数（秒）で上書きできます（デフォルト 60 秒）。

Q: OpenAI を使うためにどの環境変数を設定すればよいですか？  
A: OPENAI_API_KEY を設定してください。AI 関数では引数でキーを渡すこともできます。

---

この README はコードベースの主要機能と使い方の概要を記したものです。詳細な仕様や設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）は別途参照してください。必要があれば各モジュールごとの詳しいドキュメント（関数説明・引数・戻り値の表記）を追記します。