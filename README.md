# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、実行監視（Monitoring）、Research／AIユーティリティなどを含みます。

---
## プロジェクト概要
- 自動売買の実行エンジン、監視（プロセス / リソース / 注文 / リスク）および補助ツールを提供します。
- DuckDB を用いた分析用データ、SQLite を用いた監視・発注ログの永続化を想定しています。
- paper_trading（ペーパートレード）モードと live（本番）モードをサポート。paper_trading では本番 DB と分離された専用 SQLite を使用します。
- OpenAI（gpt-4o-mini 等）を使ったニュースNLP・レジーム判定モジュールを含みます（API キーが必要）。

---
## 主な機能一覧
- 実行（Execution）
  - ブローカークライアントの抽象化（本番/モック切替）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - Execution 起動スクリプト（run_execution.py）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク / プロセス稼働 / データ鮮度
  - TradeMonitor: 発注ログ・滞留注文・約定異常検出（trade_logs 等）
  - RiskMonitor: ドローダウン・ポジション数上限検出、ダッシュボード更新
  - KillSwitch: 条件により data/kill.flag を作成して Execution を停止
  - MonitoringEngine / run_monitoring.py によるポーリングループ
  - SQLite 監視 DB スキーマ管理（monitoring_db.py）
- ポートフォリオ構築（純粋関数群）
  - 候補選定（score ソート）、等配分／スコア重み、セクター制約、ポジションサイズ計算
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、ファクター統計要約
  - DuckDB を利用した SQL + Python 実装
- AI（OpenAI）関連
  - ニュース NLP による銘柄ごとのセンチメントスコア化（ai_scores へ格納）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
  - API 呼び出しはリトライ・フォールバック実装（5xx / 429 / タイムアウト等）
- ユーティリティ
  - 環境変数管理（.env 自動読み込み / .env ウィザード）
  - 設定検証 CLI（設定ファイル / .env の事前チェック）
  - ロギングセットアップ（コンソール＋日次ローテート）
  - プロセス優先度・CPU affinity の簡易設定

---
## セットアップ手順（ローカル開発向け）
前提: Python 3.10+（コードは typing union syntax 等を使用）

1. リポジトリをクローン／チェックアウト
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   - 注意: sqlite3 は標準ライブラリ。DuckDB と psutil は OS に依存したビルドが必要な場合があります。

4. .env の作成
   - 対話型ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でルートに .env を配置（.env.example を参考に）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能利用時）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）

5. 設定検証
   - python -m kabusys.validate_config
   - 本番に近いチェックを行う場合は --strict を使用して警告も失敗扱いにできます。

6. データディレクトリ / ログディレクトリ作成（必要であれば）
   - data/、logs/ 等は実行時に自動作成されますが、権限等で失敗する場合は手動で作成してください。

---
## 使い方（主要スクリプト）
- 実行エンジン（Execution）
  - 起動: python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 起動中は data/execution.pid ファイルを作成する
    - プロセス優先度を 'high' に設定（psutil を使用）

- 監視ループ（Monitoring）
  - 起動: python -m kabusys.run_monitoring
  - 特徴:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を参照）
    - 止めるには data/stop_requested.flag を作成（または KeyboardInterrupt）
    - SystemMonitor が監視結果を SQLite に永続化

- Paper Trading 検証レポート（ツール）
  - 実行: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数を指定するか --db で DB パスを渡せます。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- AI 関連（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 呼び出しは DuckDB 接続オブジェクトを渡す設計

---
## 主要環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）

注意: .env は絶対に Git にコミットしないでください（API キー等の機密が含まれるため）。

---
## ディレクトリ構成（概観）
以下は主要ファイル／モジュールの一覧（src/kabusys 配下）。実際はこのツリーをルートに配置し、パッケージとして利用します。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ + 永続化 API
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （注文関連監視 — 実装あり）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書込による停止
    - alert_manager.py        — （通知管理）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - broker_factory.py       — BrokerClient の生成（本番/モック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
    - news_nlp.py             — OpenAI を使ったニューススコアリング
    - regime_detector.py      — レジーム判定（MA200 + マクロセンチメント）
    - __init__.py
  - data/                     — 実行時 DB/フラグ/ログ等（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）
  - tools/
    - paper_verification_report.py
    - __init__.py

（monitoring, execution 以下にはさらに多くの補助モジュールがあります。README には主要なものを抜粋しています。）

---
## 注意点 / 運用上の留意事項
- .env に機密情報（API キーやパスワード）を保存する場合は、ファイルを Git から除外してください（.gitignore に追加）。
- Monitoring は既定で本番 SQLite を参照します。テスト環境で監視を書き換えたくない場合はパスを確認してください。
- OpenAI API 呼び出しはコストが発生します。API キーの取り扱い、レート制限に注意してください。モジュールは一部リトライ／フォールバックを実装していますが、運用では適切なレート管理を行ってください。
- process priority / cpu affinity の設定は psutil を使います。権限不足で設定ができない場合は警告ログが出てスキップされます。
- ログ: デフォルトは logs/<app_name>.log（TimedRotatingFileHandler: 日次、30日保持）。ログディレクトリに書ける権限が必要です。

---
## よく使うコマンド例
- .env 作成ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動（バックグラウンドで実行するときはプロセスマネージャを使用）
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---
もし README に追記してほしい具体的な点（たとえば構成図、シーケンス図、config/*.yaml の具体例、開発用の Dockerfile、CI 設定例など）があれば教えてください。必要に応じて追補・抜粋を作成します。