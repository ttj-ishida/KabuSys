# KabuSys

日本株自動売買システムのサンプル実装（ライブラリ/ツール群）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- Execution:
  - 発注エンジン（ExecutionEngine）と関連コンポーネント（OrderManager / RiskManager / Reconciler / OrderRepository）。
  - 本番（live）とペーパートレーディング（paper_trading）を分離して実行可能。ペーパートレード時は MockBrokerClient を使用し、専用 SQLite DB に記録します。
- Monitoring:
  - システム稼働状態、注文の滞留・約定異常、リスク（ドローダウン・ポジション上限）を監視。
  - Kill Switch（flag ファイル）で ExecutionEngine を安全に停止。
  - 監視データは SQLite（デフォルト data/monitoring.db）へ永続化。
- Research:
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）、特徴量探索、IC 計算など。
  - DuckDB を利用した分析処理（prices_daily / raw_financials 等のテーブル参照）。
- AI:
  - ニュース NLP（OpenAI を利用したセンチメントスコアリング）と市場レジーム判定（LLM + ETF MA の組合せ）。
- Tools:
  - Paper Trading の検証レポート生成スクリプト等。
- Utilities:
  - プロセス優先度・CPU affinity 設定、設定ロード/ウィザード、設定検証ツール等。

設計上の留意点:
- 環境変数を中心に設定管理（.env 自動ロード機構 / config ウィザードあり）。
- 本番 DB とペーパートレード DB は明確に分離。
- LLM（OpenAI）呼び出しは失敗時にフォールバックし、部分失敗に強い設計。

---

## 機能一覧

- 設定
  - 対話式 .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]
- 実行系
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading 時は専用 DB を使用（data/paper_trading.db、環境変数で変更可能）
    - 停止は data/stop_requested.flag の作成または kill.flag により制御
- 監視系
  - SystemMonitor をポーリングする起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
    - 監視は常に本番 sqlite_path を参照（環境に依らず）
- AI / データ
  - ニュースセンチメントスコア生成（OpenAI 使用）: kabusys.ai.score_news (内部 API)
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- リサーチ
  - ファクター計算（momentum, value, volatility）
  - 将来リターン、IC、統計サマリ等
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## セットアップ手順

前提
- Python 3.10 以上（型記法や一部機能のため）
- SQLite（標準ライブラリに含まれます）
- OS によっては psutil の一部機能で管理者権限が必要になる場合があります

1. リポジトリをクローン / 配置
   - プロジェクトルートに `src/` があり、パッケージは `kabusys` 配下に配置されています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限の依存（例）:
     - pip install duckdb psutil openai
   - 開発・検証用に PyYAML を使う機能があるため必要なら:
     - pip install pyyaml
   - （実際の requirements.txt がある場合はそれを使用してください）

4. .env の作成
   - 対話ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は `.env.example` を参照して `JQUANTS_REFRESH_TOKEN` と `KABU_API_PASSWORD` 等の必須値を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題が見つかったら .env を修正してください。
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - run_execution / run_monitoring を実行すると必要なテーブルが自動作成されます（monitoring 用テーブルは init_monitoring_db により冪等作成）。

環境変数の主要項目（代表例）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（INFO 等）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH 等（必要なら上書き）

---

## 使い方

基本的なコマンド例:

- .env を作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - ペーパートレードで起動するには .env の KABUSYS_ENV=paper_trading を設定してください。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は PID を data/execution.pid に書きます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒）
  - 監視は常に本番 sqlite_path を使用します（環境に関わらず）

- Kill Switch（Execution 停止）
  - KillCondition が満たされると monitoring が data/kill.flag を書き、Execution 停止を促します。
  - 手動で停止する場合は data/stop_requested.flag（監視スレッドの終了フラグ）や kill.flag を作成できます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を手動指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（例: ニューススコア）
  - 呼び出し関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。

ログ設定
- LOG_LEVEL 環境変数で変更（例: LOG_LEVEL=DEBUG）

停止とクリーンアップ
- Execution の安全停止は monitoring が kill.flag を書くことで行います。手動で kill.flag を削除するにはファイルを削除してください（KillSwitch.clear を利用するパターンもあります）。
- stop フラグ: data/stop_requested.flag を作成すると run_monitoring / run_execution のループは検知して終了します。

---

## ディレクトリ構成

以下は主要ファイル/ディレクトリの要約（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py
    - __init__.py
  - execution/
    - broker_factory.py (ブローカクライアント生成)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - risk_manager.py
    - …（関連実装）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/  (実行時に生成されることが多い)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (default DUCKDB)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - config/ (YAML 設定ファイル群: system_config.yaml 等)
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

補足:
- monitoring_db.init_monitoring_db は必要なテーブルを冪等に作成・マイグレーションを行います。
- DuckDB は分析用テーブル（prices_daily, raw_financials, raw_news など）を想定しています。
- OpenAI との連携機能は API キーの設定とリトライ/フォールバックロジックを含んでいます。

---

## 注意事項 / ベストプラクティス

- .env は機密情報を含むため、決してリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）での実行前に必ず `python -m kabusys.validate_config` で設定を確認してください。
- OpenAI キーやブローカ認証情報の管理は慎重に行ってください（アクセス権限・ローテーション）。
- psutil の一部 API（プロセス優先度変更など）は権限不足で失敗します。ログに警告が出るだけでプロセスは継続する設計です。
- Paper Trading を実運用検証に使う場合、必ず専用 DB（PAPER_TRADING_SQLITE_PATH）を使用してください。本番 DB と混同しないでください。

---

必要に応じて README を拡張します（例: 実行シーケンス図、API リファレンス、config/*.yaml の説明、テスト手順など）。どの情報を追加したいか教えてください。