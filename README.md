# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。

このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、OpenAI を用いたニュース NLP などの機能を含む自動売買プラットフォームの一部です。

## プロジェクト概要

- 目的: 日本株の自動売買を支援するためのライブラリ群と起動スクリプト群。
- 主な機能:
  - Strategy / Research: ファクター計算（モメンタム、ボラティリティ、バリュー等）や特徴量解析。
  - Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制約・レジーム調整。
  - Execution: 発注エンジン（本番・ペーパーの分離、ブローカーファクトリ、注文管理、リスク管理）。
  - Monitoring: システム状態監視、トレード監視、リスク監視、Kill Switch。
  - AI: OpenAI を使ったニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
  - Utils: ロギング設定、プロセス優先度設定、設定読み込みユーティリティ。
  - Tools: Paper Trading の検証レポート生成スクリプト等。
- エントリポイント:
  - 実行エンジン: python -m kabusys.run_execution
  - 監視ループ:   python -m kabusys.run_monitoring
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証:     python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report

## 機能一覧（抜粋）

- 環境/設定管理
  - .env 自動読み込み、対話式ウィザード（config_setup）、起動前検証（validate_config）
- ロギング
  - 統一的な setup_logging：コンソール stdout + 日次ローテーションファイル（logs/<app>.log）
- 実行エンジン
  - 本番 / ペーパー切替（KABUSYS_ENV）
  - Paper Trading は MockBrokerClient を利用して data/paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度設定（high/normal/low）
  - PID / stop flag による起動・停止管理（data/execution.pid, data/stop_requested.flag）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在チェック、データ鮮度確認
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine に停止シグナル送出
  - MonitoringEngine: 上記モニタをまとめてポーリング・アラート発火
- 研究・分析
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - Feature exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュース記事を集約し OpenAI（gpt-4o-mini 等）でセンチメント評価、ai_scores テーブルへ書込み
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（稼働率 / 注文成功率 / レイテンシ等の評価）

## 前提・依存関係

- Python 3.10+
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- 追加: SQLite（標準で利用可能）、ファイル書き込み権限

（requirements.txt は本リポジトリに含まれていない場合があるため、環境に応じて上記パッケージをインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

## セットアップ手順

1. レポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要なパッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルート）:
     - 必須環境変数:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 推奨 / 例:
       - KABUSYS_ENV=development  # development | paper_trading | live
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       - LOG_LEVEL=INFO
       - OPENAI_API_KEY=sk-...
       - PAPER_FILL_MODE=instant   # instant | partial | never | reject
       - KILL_FLAG_CLEAR_ON_START=0

   - 自動読み込みについて:
     - デフォルトで .env/.env.local が自動ロードされます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ等の作成（必要に応じて）
   - logs/、data/ ディレクトリは自動作成されますが権限等で失敗する場合があります。手動で作成しておくと安心です。

## 起動・使い方

- 実行エンジン（ExecutionEngine）起動:
  - 本番・ペーパーは KABUSYS_ENV によって切替
  - python -m kabusys.run_execution
  - 実行中に停止するには data/stop_requested.flag を作成するか、モニタリング側が kill.flag を書き込むとエンジンに停止シグナルが送られます。
  - ExecutionEngine の PID は data/execution.pid に記録されます（設定により変更可）。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - run_monitoring は monitoring 用 DB（Settings.sqlite_path）を使用します。Monitoring は KABUSYS_ENV に関係なく sqlite_path を使用する設計です。
  - 停止はプロジェクトルート/data/stop_requested.flag を配置。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

- OpenAI を使う処理（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY 環境変数を設定するか、各関数の api_key 引数で渡す必要があります。
  - 失敗耐性が組み込まれており、一部失敗時は安全側にフォールバックします（例: macro_sentiment=0.0）。

- ログ
  - logs/<app>.log に日次でローテートされ保存されます（30 日分保持）。
  - コンソールは stdout に出力されます。

- 停止フロー / Kill Switch
  - KillSwitch は RiskMonitor などの結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

## 主要設定・環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector 等で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の成行埋め方（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

## ディレクトリ構成（主なファイル）

プロジェクトルート（src/kabusys を想定）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - data/                     — データファイル群（実行時に作成される）
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
  - research/
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — 将来リターン / IC / summary
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層 / DB マイグレーション
    - system_monitor.py
    - trade_monitor.py        — （実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （実装あり）
  - execution/
    - execution_engine.py     — ExecutionEngine（実装あり）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - research/、data/、tools/ 等の追加モジュール

（上記は主要ファイルの抜粋です。細かい実装はソースツリーを参照してください。）

## 開発時の注意点 / 運用メモ

- Paper Trading は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を指定）。
- Monitoring は run_monitoring が使用する sqlite_path を環境にかかわらず直接参照するため、本番 DB のパス管理に注意してください。
- ローカルでテストするときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にしてテスト用の環境変数注入を行うと便利です。
- OpenAI API 呼び出しはレート制限や一時エラーを考慮してリトライ実装がありますが、API キーやコスト管理を適切に行ってください。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（本番で kill.flag が消えてしまう可能性があるためデフォルト 0 を推奨）。

## よくあるコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README にサンプル .env 内容、さらに細かい設定項目の説明や運用フロー（デプロイ手順、systemd ユニット例、監視・アラート設定例）を追加します。どの情報を追加したいか教えてください。