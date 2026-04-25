# KabuSys

日本株自動売買システムの骨格ライブラリ。戦略・ポートフォリオ構築・発注エンジン・監視・研究/ファクター計算・AI ニュース解析などを含むモジュール群を提供します。

注意: 本リポジトリはアプリケーション本体のロジック・ユーティリティ群を含みます。実行環境の設定 (.env)、DB（SQLite / DuckDB）、および外部 API キーは利用者側で準備してください。

## 概要

- 発注実行（ExecutionEngine）および監視（MonitoringEngine）向けの起動スクリプトを備え、実行・監視を分離して運用可能。
- Paper Trading モードを備え、本番 DB と分離して動作（MockBrokerClient を使用）。
- DuckDB を分析 / 研究用データストアとして使用、SQLite を監視 / 発注ログ用に使用。
- ニュースの自然言語処理（OpenAI API）を用いた銘柄センチメント評価および市場レジーム判定モジュールを実装。
- ポートフォリオ構築（候補選定・重み計算・リスク調整・株数決定）やファクター計算 / 解析機能を提供。
- ロギング・プロセス優先度設定・Kill Switch（フラグファイル）など、運用用ユーティリティを備える。

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py — SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 設定関連
  - config_setup.py — .env 対話式ウィザード（.env の初期作成 / 更新）
  - validate_config.py — 環境変数 / config/*.yaml の検証 CLI
  - Settings クラス — 環境変数の集中管理
- 監視
  - monitoring/monitoring_db.py — SQLite スキーマ初期化・読み書き
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py — 監視ロジックとアラート連携
  - kill_switch.py — フラグファイルで Execution を停止する仕組み
- 発注・実行（実行エンジン関連）
  - execution/* — BrokerFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository など（発注・リスク管理）
  - Paper Trading: 設定で MockBrokerClient を使い data/paper_trading.db に記録
- ポートフォリオ構築
  - portfolio/portfolio_builder.py — 候補選定、等重・スコア重み
  - portfolio/position_sizing.py — 株数決定、ロット丸め、aggregate cap
  - portfolio/risk_adjustment.py — セクター上限、レジーム乗数
- 研究（Research）
  - research/factor_research.py — Momentum / Volatility / Value 等ファクター計算（DuckDB ベース）
  - research/feature_exploration.py — 将来リターン、IC 計算、統計サマリー
- AI
  - ai/news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores へ書き込み
  - ai/regime_detector.py — マクロニュース + ETF MA を使ったレジーム判定
- ツール
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成 CLI
- ユーティリティ
  - utils/logging_setup.py — 統一ロギング設定（stdout + 日次ローテーション）
  - utils/process_priority.py — プロセス優先度・CPU affinity 設定

## セットアップ手順

1. Python 環境
   - Python 3.9+ を推奨（duckdb, psutil, openai 等の互換性に応じて調整してください）。

2. 依存パッケージ（例）
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml の構文チェック用）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他主要環境変数（デフォルトがあるものも記載）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY — AI モジュール利用時に必要
     - LOG_LEVEL — デフォルト: INFO
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
   - 設定検証:
     - python -m kabusys.validate_config
     - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

4. DB 初期化
   - run_execution / run_monitoring の起動時に必要テーブルは自動で初期化されます（monitoring_db.init_monitoring_db）。

5. ログディレクトリ
   - デフォルトで logs/ に日次ローテートされるログが出力されます。必要に応じて LOG_DIR 環境変数で変更。

## 使い方（主なコマンド）

- Execution エンジンを起動（本番/ペーパートレードを Settings で切り替え）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid（PID ファイル）を管理。停止は Stop フラグ（data/stop_requested.flag）設置または Kill Switch（data/kill.flag）により制御。

- Monitoring を起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で秒間隔を変更可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（ニューススコア／レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを直接呼ぶ場合は OPENAI_API_KEY が必要（または api_key を引数で渡す）

- Kill Switch 操作（手動）
  - data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送れます（KillSwitch を通じて書き込むか、直接ファイルを作成）。

注意点:
- run_execution は KABUSYS_ENV=paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。
- monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっています（run_monitoring 内の扱いに注意）。

## ディレクトリ構成

（プロジェクトルートを起点、主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP / OpenAI スコア
    - regime_detector.py     — 市場レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照されるが該当ファイルは省略可能)
  - execution/
    - (BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等)
      ※ 実際のブローカー実装や発注ロジックは execution 配下に実装
  - data/                      — デフォルトで使用される DB / flag / pid ファイルの格納先（実行時に作成）
  - logs/                      — デフォルトログ出力先（logging_setup が作成）

## 運用・実装上の注意

- OpenAI API を利用する機能はネットワークに依存し、API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・バックオフ処理を含みますが、API 失敗時には安全にフォールバックする設計です（例: マクロセンチメント失敗時は 0.0）。
- ログ出力は共通設定を使用しており、ログディレクトリ作成に失敗するとコンソール出力のみになります。
- Kill Switch は冪等的に振る舞い、既にファイルが存在する場合は再書き込みしません。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると既存 flag を自動で削除しますが、本番では 0 を推奨します。
- settings.env によって behavior が変わります（development / paper_trading / live）。live は本番用なので設定内容（LINE 通知等）を十分に確認してください。
- DuckDB/SQLite のスキーマは init_monitoring_db によって必要なテーブル・列（マイグレーション含む）が作成されます。

## 追加情報 / 参考コマンド

- .env を生成してから設定検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- 監視をデバッグ的に1回だけ実行する（テスト向け）:
  - MonitoringEngine をテスト用にインスタンス化して run_once() を呼ぶ（コードから直接）
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は本プロジェクトの主要ポイントに絞ってまとめています。実際の運用やデプロイ時には、.env の管理（秘匿情報）、バックアップ、監視アラート設定（LINE 等）、外部 API の利用制限・コスト管理についても十分な計画を行ってください。必要であれば、各モジュール（execution/*、monitoring/*、ai/*）の詳細な設計ドキュメントを追加で作成できます。