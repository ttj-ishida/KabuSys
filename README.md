# KabuSys

日本株向け自動売買システムのライブラリ群および起動スクリプト群です。本リポジトリはトレード実行、監視、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュース解析などのコンポーネントで構成されています。

以下はこのコードベースの概要・機能・セットアップ・使い方・ディレクトリ構成の README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化したシステムです。主な機能は次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード切替対応）
- Monitoring：システム稼働状況、注文状態、リスク（ドローダウン・ポジション上限等）を監視し、必要時に Kill Switch（停止フラグ）を作動
- Portfolio Construction：銘柄選定、配分重みの計算、ポジションサイズ決定、セクター制限 等
- Research：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- AI モジュール：OpenAI（gpt-4o-mini等）を用いたニュースのセンチメント解析／市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、.env ウィザードおよび設定検証 CLI、検証レポート生成ツール

設計方針として、DB（SQLite / DuckDB）を用いた永続化・分析、LLM 呼び出しのリトライ / フェイルセーフを含む堅牢性を重視しています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを取り続ける
- 環境設定
  - config_setup.py: 対話式ウィザードで `.env` を生成 / 更新
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
- Monitoring
  - monitoring_engine.py: 各モニタ（System/Trade/Risk）を束ねるエンジン
  - monitoring_db.py: SQLite に対する監視ログ永続化層（テーブル作成・マイグレーション含む）
  - kill_switch.py: フラグファイルを用いた ExecutionEngine 停止制御
  - risk_monitor.py / trade_monitor.py / system_monitor.py: 各監視ロジック
- Portfolio（銘柄選定・重み計算・ポジションサイズ）
  - portfolio_builder.py, risk_adjustment.py, position_sizing.py
- Research（ファクター計算・特徴量探索）
  - factor_research.py, feature_exploration.py
- AI
  - ai.news_nlp: ニュース群を LLM でスコアリングして ai_scores に書き込み
  - ai.regime_detector: ETF の MA200 比やマクロ記事スコアを合成して market_regime を算出
- Tools
  - tools.paper_verification_report.py: ペーパートレード用 SQLite の検証レポート生成

---

## セットアップ手順

前提
- Python 3.9+（型アノテーションなどを利用）
- システムに sqlite と DuckDB を利用できる環境

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - pyyaml（config 検証時に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt が無い場合は上記を目安にインストールしてください）

4. .env の準備
   - 対話式で作成:
     - python -m kabusys.config_setup
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主なオプション / デフォルト
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を利用する場合に必要
     - PAPER_FILL_MODE: instant | partial | never | reject （ペーパートレードの約定モード）
   - .env は絶対に Git にコミットしないでください（config_setup が注意書きを出力します）

5. ログディレクトリ
   - デフォルトで `logs/` を作成します。WRITE 権限を付与してください。
   - 環境変数 LOG_DIR で変更可能。

---

## 使い方

主な起動方法・ユーティリティの呼び出し例を示します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパー両対応）
  - python -m kabusys.run_execution
  - 動作
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離
    - 起動時に data/stop_requested.flag が既に存在するとエンジンは起動しません
    - data/execution.pid に PID を書きます（Engine の管理用）
    - 停止は data/stop_requested.flag の作成により行います（Kill Switch とは別）
    - 起動前に KILL_FLAG_CLEAR_ON_START=1 のときは kill flag を自動クリア（本番では 0 推奨）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作
    - SystemMonitor をポーリングして system_status などを SQLite に記録
    - デフォルトポーリング間隔: 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）
    - 監視は常に本番用の sqlite_path を使用（監視データは本番 DB に保存）
    - data/stop_requested.flag を検知すると監視ループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （あるいは環境変数 PAPER_TRADING_SQLITE_PATH）

- AI モジュール（プログラム的に利用）
  - ニューススコア付与（例）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")
  - レジーム判定（例）
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="sk-...")
  - 注意点
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で渡す
    - API 呼び出しはリトライロジックを備え、失敗時はフェイルセーフ（0 や既定値）で継続する設計

- Kill Switch 操作
  - kill_switch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります
  - kill.flag のパスは Settings.kill_flag_path で指定可能（デフォルト: data/kill.flag）
  - ExecutionEngine 側は起動時にこのフラグを確認し、適宜動作を制御します

---

## 重要なファイル / 環境変数（抜粋）

- .env（推奨して作成）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development|paper_trading|live)
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
  - OPENAI_API_KEY（AI 機能利用時）
  - LOG_LEVEL（デフォルト INFO）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）

- フラグ / PID ファイル（デフォルトパス）
  - data/stop_requested.flag: run_* スクリプトが監視している停止フラグ
  - data/kill.flag: Kill Switch が作成する ExecutionEngine 停止フラグ
  - data/execution.pid: ExecutionEngine の PID

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys/` 以下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理
  - config_setup.py             — .env 対話式ウィザード CLI
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py          — SQLite テーブル初期化・永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py          — （実装されているはずのアラート送信ロジック）
  - execution/                  — ExecutionEngine・OrderManager 等（発注ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング
    - regime_detector.py        — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はコードベース内で提供されている主要コンポーネントの一覧です。execution パッケージ内は発注・ブローカー抽象化などの詳細実装が存在します。）

---

## ログ / DB / マイグレーション

- ログ
  - logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30日保持）
  - コンソールは stdout に出力（cron/シェルからの集約に便利）

- DB
  - monitoring_db.init_monitoring_db(conn) はテーブル作成・簡単なマイグレーション処理を行います（冪等）
  - ペーパートレード用 DB は KABUSYS_ENV=paper_trading 時に PAPER_TRADING_SQLITE_PATH を使用して分離します
  - DuckDB は分析用に使用（prices_daily / raw_financials 等を想定）

---

## 動作上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env の値を十分に検証してください（validate_config を必ず実行）
- KILL_FLAG_CLEAR_ON_START は本番で 1 にしないでください（Kill Switch が自動クリアされてしまいます）
- OpenAI API を使用する機能は API 利用料が発生するため用途・呼び出し頻度を注意して設定してください
- ファイルベースのフラグ（stop_requested.flag / kill.flag）を利用してプロセス制御を行うため、権限やパスに注意してください
- psutil を利用してプロセス優先度・CPU affinity を設定しますが、環境によっては権限が必要です（set_process_priority）

---

## 開発者向け・テスト

- 各モジュールは純粋関数で実装されている箇所が多く、ユニットテストが比較的書きやすい設計です（例: portfolio、research 部分）
- AI API 呼び出し部分は _call_openai_api の差し替え（モック）でテストが容易になる設計になっています
- validate_config は --strict オプションで警告を厳格に扱えます
- monitoring_db の初期化は冪等なのでローカル実行時に何度でも実行できます

---

README は主要な使い方と運用上の注意をカバーしています。特定の機能（ExecutionEngine の詳細設定や BrokerClient の実装、アラート送信先の設定など）については該当モジュールのドキュメントやソースコメントをご参照ください。必要であれば、各モジュールの使い方・API ドキュメントを追加で作成します。