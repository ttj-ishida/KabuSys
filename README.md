# KabuSys

日本株自動売買システムの基礎モジュール群（README）。  
このドキュメントはリポジトリ内の主要なスクリプト・モジュールをまとめ、セットアップ・起動方法を示します。

- 対象コード: src/kabusys 以下のモジュール群
- 対応 Python: 3.10 以上（typing の union 記法や modern 型ヒントを想定）

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定した内部ライブラリ群です。主な責務は以下のとおりです。

- データ処理 / 研究用ファクター計算（DuckDB 経由）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング）
- ExecutionEngine（発注ロジック）とそれを支えるブローカー抽象
- 監視（System / Trade / Risk）と Kill Switch（危険時に Execution を停止）
- Paper Trading 用ツールと検証レポート生成
- ニュースの NLP（OpenAI）を用いたセンチメント評価、レジーム判定

設計上の特徴：
- 環境変数による設定（.env を利用）
- paper_trading と live を分離（paper_trading は MockBroker＋専用 DB）
- DuckDB を分析用 DB、SQLite を監視・ログ保存に利用
- Logging は共通ユーティリティで設定（stdout + 日次ローテートファイル）

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動読み込み（.env/.env.local、ただし環境変数が優先）
  - config_setup（対話式ウィザード）で .env を作成
  - validate_config で設定検証（--strict オプションあり）

- 実行系
  - run_execution.py：ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBroker + data/paper_trading.db を使用
    - 実行中は PID ファイルを生成（data/execution.pid）
  - run_monitoring.py：SystemMonitor のポーリング起動スクリプト
    - MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）

- 監視
  - system_monitor / trade_monitor / risk_monitor を束ねる MonitoringEngine
  - KillSwitch（data/kill.flag）で ExecutionEngine 停止をシグナル
  - monitoring_db モジュール：SQLite スキーマ管理・永続化 API

- ポートフォリオ関連（純粋関数）
  - 候補選定（select_candidates）
  - 重み計算（等分/スコア加重）
  - セクター上限・レジーム乗数適用
  - 単元丸め・リスクベースの株数算出

- 研究 / ツール
  - factor_research（momentum/value/volatility の計算）
  - feature_exploration（IC、forward returns、統計サマリ等）
  - tools/paper_verification_report：ペーパートレード検証レポート生成

- AI（OpenAI）
  - news_nlp.score_news：ニュース記事を LLM でセンチメント評価し ai_scores に書き込み
  - regime_detector.score_regime：ETF MA + マクロセンチメントで市場レジーム判定

---

## セットアップ手順

1. リポジトリを取得
   - git clone などで取得し、プロジェクトルート（pyproject.toml または .git がある場所）で操作してください。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（代表例）
   - pip install duckdb psutil openai
   - PyYAML は validate_config の YAML 検証に任意で必要：pip install pyyaml
   - （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. .env の作成
   - 対話式で作成:
     - python -m kabusys.config_setup
   - 手動例（プロジェクトルート/.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...  (AI 機能を使う場合)

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ や logs/ を使います。実行時に自動作成されますが、権限等に注意してください。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
  - live: 実運用。注意して設定してください

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログ設定（utils.logging_setup を参照）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

---

## 使い方（起動例・コマンド）

- 環境作成・検証（例）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、PAPER_TRADING_SQLITE_PATH を使い本番 DB と分離
    - 起動時に data/execution.pid を作成し、data/stop_requested.flag の存在で停止を検出
    - プロセス優先度を high にセットしようとします（失敗しても継続）

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL でポーリング間隔を設定（デフォルト 60 秒）
    - monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH: SQLite DB ファイルを明示的に指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 標準出力にレポートを表示（稼働率、成功率、レイテンシ等）

- Kill Switch の操作
  - kill_switch は data/kill.flag を作成すると Execution に停止命令を出す設計です（KillSwitch クラス参照）。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされます（本番では 0 推奨）。

- プログラム API の利用（例）
  - AI によるニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  — DuckDB 接続を渡して実行
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

---

## ロギング

- ユーティリティ: kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼出し統一
- 出力:
  - コンソール (stdout)
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30 日保持）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定

---

## 停止方法

- 実行中の監視またはエンジンは以下のフラグファイルを監視します。
  - data/stop_requested.flag — run_monitoring/run_execution で監視され停止トリガーに
  - data/kill.flag — KillSwitch によって作成され、Execution を強制停止させるためのフラグ
- 通常はシグナル（Ctrl+C）でも停止できます。自動運用では stop_requested.flag を書くことで停止制御できます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトルート（pyproject.toml がある想定）
- src/
  - kabusys/
    - __init__.py
    - run_execution.py
    - run_monitoring.py
    - config.py                  — 環境変数・Settings
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - utils/
      - __init__.py
      - logging_setup.py         — ログ設定ユーティリティ
      - process_priority.py      — プロセス優先度 / CPU affinity
    - monitoring/
      - __init__.py
      - monitoring_db.py         — SQLite スキーマ + DB ラッパ
      - system_monitor.py
      - trade_monitor.py         — （存在する前提のモジュール）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py         — （アラート通知の管理、存在することが期待される）
    - execution/
      - broker_factory.py        — ブローカークライアント生成
      - execution_engine.py      — ExecutionEngine 実装
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
    - ai/
      - __init__.py
      - news_nlp.py               — ニュース NLP / OpenAI 呼び出し
      - regime_detector.py
    - monitoring/ (上に記載済)
    - tools/
      - __init__.py
      - paper_verification_report.py

（注）ファイル一覧は抜粋/要約です。各モジュールの内部実装は主要関数に docstring があり、利用方法や引数・戻り値が明記されています。

---

## 注意事項 / 運用上の留意点

- KABUSYS_ENV=live 設定時は本番運用です。LINE 通知や kill flag の設定等、十分に確認してください。
- paper_trading モードは本番 DB を汚さない設計ですが、DB パスの設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を利用する機能は API キーと利用料金が必要です。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、課金等に注意してください。
- ローカルでの開発・検証は KABUSYS_ENV=development を推奨します（発注を行わない等の保護が行われる想定）。

---

## 参考コマンドまとめ

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python REPL で API 呼び出し
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")

---

README は以上です。必要ならば各モジュールごとの詳細ドキュメント（API シグネチャ、例、ユースケース）を追加で生成します。どのモジュールのドキュメントを優先して欲しいか教えてください。