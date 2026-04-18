# KabuSys — README

日本株向け自動売買 / 研究プラットフォーム「KabuSys」のリポジトリ用 README です。  
このドキュメントはリポジトリ内のコード（src/kabusys/...）に基づき、プロジェクト概要・機能・セットアップ・使い方・主要ディレクトリ構成を日本語でまとめています。

注意: この README はコードベースを参照して作成しています。実運用前に `python -m kabusys.validate_config` で設定検証を行い、十分なテストを実施してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を備えた統合システムです。

- 市場データ（DuckDB 経由）を用いたファクター計算・特徴量生成（研究モジュール）
- ポートフォリオ構築（候補抽出、重み付け、ポジションサイズ計算）
- ExecutionEngine による発注管理（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk モニタ）と Kill Switch による自動停止
- LLM（OpenAI）を使ったニュースのセンチメント評価・市場レジーム判定
- ペーパートレード検証レポート生成ツール

設計方針の一部:
- DB（SQLite / DuckDB）をデータ永続化に利用
- 本番・ペーパートレードは DB を分離
- 可能な箇所はフェイルセーフ（API障害時に安全なデフォールト）を採用
- ルックアヘッドを避ける設計（内部で日付や時刻を直接参照しない等）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートから .env/.env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 起動前の設定検証: python -m kabusys.validate_config (--strict)

- 実行エンジン / 発注
  - run_execution: ExecutionEngine を起動（本番 / paper_trading を切り替え）
  - ブローカークライアントの抽象化（BrokerClientFactory）

- 監視 / リスク制御
  - run_monitoring: SystemMonitor のポーリングループ
  - MonitoringEngine: System/Trade/Risk モニタを束ね、アラート管理と Kill Switch を評価
  - kill.flag による ExecutionEngine の停止指示

- 研究（Research）
  - ファクター計算: momentum / volatility / value（DuckDB を使用）
  - 将来リターン・IC（Information Coefficient）計算
  - z-score 正規化ユーティリティ連携

- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスク基準の適用（セクターキャップ）
  - ポジションサイズ計算（risk_based / equal / score）

- AI（OpenAI）連携
  - ニュース記事のセンチメント評価（news_nlp）
  - 市場レジーム判定（regime_detector）
  - OpenAI の呼び出しはリトライやバリデーションを含む堅牢な実装

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

※ 以下は一般的な手順です。実環境では適宜バージョン固定やセキュリティ対策を行ってください。

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 必須候補（コード参照）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config 検証で YAML パースをする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. 初期設定 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` をプロジェクトルートに作成。最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - （AI 機能を使う場合）OPENAI_API_KEY
   - デフォルト値（コード内デフォルト）:
     - DUCKDB_PATH = data/kabusys.duckdb
     - SQLITE_PATH = data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
     - LOG_LEVEL = INFO
     - KABUSYS_ENV = development（valid: development / paper_trading / live）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります

6. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 配下に DB / PID / フラグファイルが置かれます。自動で作成される箇所もありますが、権限等で失敗する場合があります。

---

## 使い方（起動・CLI）

- ExecutionEngine を起動（本番または paper_trading）
  - KABUSYS_ENV によって挙動が変わります。
    - KABUSYS_ENV=paper_trading → MockBrokerClient を使用し paper DB（PAPER_TRADING_SQLITE_PATH）に記録
  - 実行:
    - python -m kabusys.run_execution

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 実行:
    - python -m kabusys.run_monitoring

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- プログラム的な利用（ライブラリ呼び出し）
  - 研究モジュール例:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - conn = duckdb.connect("data/kabusys.duckdb"); calc_momentum(conn, target_date)
  - AI モジュール:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")

- 強制停止 / Kill Switch
  - kill.flag（Settings.kill_flag_path、デフォルト: data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送る仕組みがあります
  - run_* スクリプトは data/stop_requested.flag の存在によってループを終了します（stop 用のフラグ）

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (例: DEBUG / INFO / WARNING / ERROR)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔 秒)
- PID_FILE_PATH / KILL_FLAG_PATH など（設定参照）

設定ファイル読み込みの仕様:
- OS 環境変数 > .env.local > .env の順で読み込まれます。
- 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要なモジュール構成（抜粋）です。実際のリポジトリではさらにファイルやモジュールが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM センチメント評価（ai_scores 書込）
    - regime_detector.py     — 市場レジーム判定（ma200 + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - trade_monitor.py       — （参照あり、取引ログ監視等）
    - alert_manager.py       — （参照あり、通知管理）

  - execution/               — Execution 関連（Engine, OrderManager, BrokerFactory, 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・キャップ・丸め
    - risk_adjustment.py      — セクター制限・レジーム乗数

  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value 等の計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー

  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

  - utils/
    - __init__.py
    - logging_setup.py        — ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py     — process priority / CPU affinity 設定ユーティリティ

---

## 運用上の注意 / 参考

- Monitoring と Execution は別プロセスとして運用される想定で、監視は production sqlite_path を参照します（run_monitoring は環境に関係なく sqlite_path を使用）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に完全分離して書き込みます（実口座と混ざらない）。
- Kill Switch（kill.flag）や stop_requested.flag による制御機構があるため、運用時のフラグファイルの取り扱いに注意してください。
- OpenAI 呼び出しは外部 API に依存します。API キーや料金、レート制限の管理を行ってください。AI 部分は API エラーに対するリトライやフォールバック（0.0）を備えていますが、結果の品質は LLM の出力に依存します。
- DB スキーマは init_monitoring_db で自動作成・マイグレーションを行いますが、既存データに対する変更は注意して行ってください。

---

## 追加情報 / 開発者向け

- ロギング: kabusys.utils.logging_setup.setup_logging を起動コードで最初に呼ぶことで、統一的なログ出力を得られます（stdout + logs/<app_name>.log へ日次ローテーション）。
- プロセス優先度: set_process_priority("high") 等でプロセス優先度を設定します（psutil を利用、権限により失敗する場合あり）。
- DuckDB を使って大規模な時系列・財務データを効率的に処理する想定です。研究用クエリは DuckDB 接続を受け取り純粋関数で計算します。

---

もし README に追加したい項目（API ドキュメント、具体的な .env.example、docker / systemd ユニット例、CI 設定、依存パッケージの固定バージョンなど）があれば教えてください。それらを反映した詳細 README を作成します。