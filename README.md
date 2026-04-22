# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）のリポジトリ。  
この README はコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: .env には機密情報（API トークン等）が含まれます。絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買（ExecutionEngine）・監視（Monitoring）・リサーチ（ファクター計算／特徴量解析）・ポートフォリオ構築・AI（ニュースセンチメント）といった機能を含むモジュール群です。  
主要な設計方針としては以下を採用しています。

- コンポーネント分離：監視・発注・リスク管理・アラートを分けて実装
- DB 分離：Paper Trading は本番の SQLite DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- フェイルセーフ：API 失敗時やデータ不足時は安全側にフォールバック
- DuckDB を分析用 DB に利用、SQLite を監視・発注ログ用に利用
- OpenAI を用いたニュース NLP（オプション）

---

## 主な機能一覧

- 実行（Execution）
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper / live 切替）
  - Broker クライアントの抽象化（本番 / Mock 切替）
  - OrderManager / RiskManager / Reconciler 統合

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: SystemMonitor、TradeMonitor、RiskMonitor を統合して定期実行
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringDB: SQLite に監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を永続化

- ポートフォリオ構築
  - 銘柄選定（score / rank ベース）、等金額配分、スコア加重配分
  - 単元株丸め・リスクベースの数量算出・セクター制限など

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（オプション）
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores への書き込み）
  - regime_detector: MA200 とマクロニュースを組合せて市場レジーム判定（market_regime テーブル書込）

- ユーティリティ
  - config_setup.py: .env の対話式ウィザード（初期設定）
  - validate_config.py: 起動前の設定検証 CLI（--strict オプションあり）
  - tools/paper_verification_report.py: Paper Trading 検証レポート出力
  - logging_setup / process_priority: ロギング・プロセス優先度設定ユーティリティ

---

## 前提・依存ライブラリ

主な外部依存（例）:
- Python 3.9+
- duckdb
- psutil
- openai (ai モジュールを使用する場合)
- PyYAML（validate_config の YAML 検証、任意）
- （SQLite は標準ライブラリに含まれます）

推奨インストール例（仮の requirements）:
pip install duckdb psutil openai PyYAML

※ 実際の requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします。
   - pip install duckdb psutil openai PyYAML

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
     - ウィザードは .env を生成します（デフォルト: プロジェクト直下の .env）。
     - J-Quants / kabuAPI のトークン等を入力します。
   - 既存 .env を手動作成する場合は .env.example を参考にしてください（リポジトリにない場合はスクリプトの ITEMS を参照）。

4. 設定を検証します。
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告もエラー扱いになります。
     - python -m kabusys.validate_config --strict

5. データディレクトリの初期作成（任意）
   - デフォルト DB / ログ / data ディレクトリは起動時に自動作成されますが、必要なら手動で作成してください。
   - デフォルトパス（Settings のデフォルト）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - ログディレクトリ: logs/

注意:
- 自動環境変数ロード: プロジェクトルートに .env/.env.local が存在すれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- .env は機密情報を含むため Git 管理から除外してください。

---

## 実行方法（代表的なコマンド）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag があると起動せず終了します。
  - プロセス PID は data/execution.pid に書き込みます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は Settings.sqlite_path（production 相当の monitoring DB）を使用します（環境にかかわらず本番 sqlite_path を参照）。

- .env 対話式作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があっても exit(1) で失敗扱いに。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH が利用可能。

- AI モジュール（ニュース NLP / レジーム判定）
  - ai モジュールは OpenAI API キー（OPENAI_API_KEY）を必要とします。
  - news_nlp.score_news や regime_detector.score_regime をコードから呼び出して使用します。
  - API エラー時は安全側のデフォルト（例: macro_sentiment=0.0）で継続する実装です。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — 必須: kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — Paper Broker の fill モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（1=yes、デフォルト 0）

---

## ファイル／ディレクトリ構成

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — Settings クラス（環境変数の読み込み・検証・デフォルト）
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメントを OpenAI でスコア化し ai_scores へ書込
    - regime_detector.py — MA200 とマクロニュースで市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化・簡易 CRUD（MonitoringDB）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態（CPU/メモリ/ディスク/データ鮮度）監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （存在する想定のモジュール：trade 関連チェック）
    - kill_switch.py — Kill Switch（data/kill.flag 書き込み）
    - alert_manager.py — （存在する想定のモジュール：アラート送信）
  - execution/
    - execution_engine.py — Execution エンジン本体（EngineConfig 等）
    - broker_factory.py — Broker クライアント生成ファクトリ（本番 / Mock 切替）
    - order_manager.py — 注文管理
    - order_repository.py — 発注ログ永続化（SQLite）
    - reconciler.py — 注文状態の整合処理
    - risk_manager.py — 実行時リスク管理（RiskConfig）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（equal / score）
    - position_sizing.py — 株数算出、lot_size 丸め、aggregate cap
    - risk_adjustment.py — セクター制限、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - utils/
    - logging_setup.py — 統一的なログ設定（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度／CPU affinity 設定ユーティリティ

上記に加え、プロジェクトルートには（存在する場合）
- .env / .env.local — 環境変数ファイル（機密情報）
- data/ — デフォルト DB / フラグファイル（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid）
- logs/ — ログファイル（例: logs/execution.log, logs/monitoring.log）
- config/ — 各種設定 YAML（system_config.yaml など。validate_config で検証）

---

## 実運用にあたっての注意点

- .env は必ず外部で安全に管理してください（機密トークンの漏洩防止）。
- KABUSYS_ENV=live を設定する際は validate_config の警告を必ず確認してください（LINE 通知や Kill Switch の設定など）。
- OpenAI を使用する機能は API コストとレート制限に注意してください。API 失敗時のフォールバックは実装されていますが、意図しない挙動は排除していないため十分な監視を推奨します。
- run_monitoring は monitoring 用 SQLite（settings.sqlite_path）を使用します。monitoring データは環境にかかわらず本番 sqlite_path に書き込む点に注意してください。
- Paper Trading は本番 DB と分離されるように設計されていますが、設定ミスで上書きしないよう DB パスを慎重に設定してください。

---

以上がリポジトリの README です。追加で「起動手順の自動化（systemd / cron）」「設定ファイルのテンプレート（config/*.yaml の生成）」「テスト実行方法」などのドキュメントが必要であれば、あなたの運用環境や要望に合わせて追記します。