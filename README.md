KabuSys — 日本株自動売買システム
================================

この README は、コードベース（src/kabusys 以下）を元に、プロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行うシステムです。  
主要な役割は次のとおりです。

- ExecutionEngine：発注・注文管理・リスク管理・実行を担うエンジン
- Monitoring：システム稼働状況・注文状態・リスクを監視し、Kill Switch による停止やアラートを発行
- Research：DuckDB を用いたファクター計算・特徴量分析
- AI モジュール：ニュースを LLM（OpenAI）で解析してスコアを生成、レジーム判定の補助
- Tools：ペーパートレードの検証レポートなど補助ツール群

主要設計方針：
- 本番環境とペーパートレードを明確に分離（SQLite 等）。
- DuckDB を分析用 DB として利用（読み取り中心）。
- 外部 API 呼び出し（OpenAI / kabuステーション / J-Quants）は設定により有効化。
- ロギング・監視・フェイルセーフ機構（Kill Switch / stop flag）を搭載。

主な機能一覧
--------------
- 環境設定ウィザード（.env の対話式生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env、config/*.yaml の検査）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録（本番 DB と分離）
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）
- 監視永続層（SQLite）: monitoring_db（system_status / trade_logs / positions / risk_logs / dashboard）
- リスク監視（ドローダウン、ポジション上限など）と Kill Switch（data/kill.flag）
- ニュース NLP（OpenAI を用いた銘柄別センチメント取得）: kabusys.ai.news_nlp.score_news
- レジーム判定（ETF MA とマクロセンチメントの合成）: kabusys.ai.regime_detector.score_regime
- 研究用モジュール（ファクター計算、IC 計算、統計サマリー）: kabusys.research.*
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

前提:
- Python 3.10+（typing 機能の一部を利用）
- システムにより追加パッケージが必要（下記を参照）

推奨依存パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config 検証の一部で使用）
- （必要に応じて）その他発注用クライアントやテスト用ライブラリ

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（例）
   - pip install duckdb psutil openai PyYAML

   （requirements.txt は本リポジトリに含まれていない場合があるため、プロジェクトの依存を確認してインストールしてください。）

3. 環境変数設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成された .env を編集して必要な値を設定してください。

   重要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD     (必須)
   - KABUSYS_ENV           (development | paper_trading | live) — default: development
   - DUCKDB_PATH           (例: data/kabusys.duckdb)
   - SQLITE_PATH           (例: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
   - LOG_LEVEL             (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - OPENAI_API_KEY        (AI 機能を使う場合に必須)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (本番アラート用、任意)

   ※ 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）を検出して .env を自動読み込みします。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

使い方
------

基本的な実行コマンド

- ExecutionEngine（本番／ペーパー共通起動）
  - python -m kabusys.run_execution
  - 動作説明:
    - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用して本番 DB と分離
    - エンジンは別スレッドで実行され、data/stop_requested.flag の作成により停止できます
  - 停止フラグ:
    - data/stop_requested.flag を作成すると、起動中の run_execution は検知して停止を試みます
  - PID 管理:
    - data/execution.pid を指定（Settings.pid_file_path）して PID 管理

- Monitoring（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更（デフォルト 60）
  - 監視は本番 sqlite_path を使用（環境に関わらず同じ監視 DB を参照）
  - 停止フラグ:
    - data/stop_requested.flag により監視ループが終了

- Kill Switch（自動停止トリガ）
  - KillSwitch は risk_monitor 等の結果に基づき data/kill.flag を作成します
  - 実行エンジンは kill.flag の存在を起点に停止処理（Settings.kill_flag_clear_on_start に注意）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または PAPER_TRADING_SQLITE_PATH 環境変数

- AI 機能（ニューススコア・レジーム判定）
  - 必須: OPENAI_API_KEY を設定
  - ニューススコア: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - conn は DuckDB 接続、target_date は date 型
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらもエラー時はフェイルセーフで継続する設計（API 失敗時はデフォルト値で処理）

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging によって設定されます。
- デフォルトログディレクトリ: logs/
- 各起動スクリプトで app_name（例: "execution", "monitoring"）を渡すことで logs/<app_name>.log に日次ローテーションで出力されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御します。

停止・強制停止
----------------
- 正常停止: run_execution / run_monitoring は data/stop_requested.flag の作成および KeyboardInterrupt (Ctrl+C) に対応します。
- Kill Switch による停止: data/kill.flag が作成されるとエンジンは停止を受けます（設定により起動時に kill.flag を自動クリアするオプションあり）。
- ファイルパス:
  - Execution PID: data/execution.pid（Settings.pid_file_path）
  - Stop フラグ: data/stop_requested.flag
  - Kill フラグ: data/kill.flag

ディレクトリ構成（主なファイル）
-------------------------------

プロジェクトルート（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定の読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュースの LLM スコアリング
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py      — システム/データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション監視
    - trade_monitor.py       — （注文監視: コードベースに含まれる想定の監視ロジック）
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各モニタを束ねるループエンジン
    - alert_manager.py       — （アラート送信の抽象化）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注・セッション管理）
    - order_manager.py       — 発注ロジック
    - order_repository.py    — 注文の永続化/読み書き
    - broker_factory.py      — ブローカークライアント生成（Mock / 実装切り替え）
    - reconciler.py          — 注文/ポジションの整合処理
    - risk_manager.py        — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py   — 候補選定・スコアソート
    - position_sizing.py     — 株数算出・資金配分ロジック
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - data/                    — 実行時生成の DB・フラグ類（リポジトリルートの data/）
  - tools/
    - paper_verification_report.py — ペーパートレード検証用レポート

補足 / 運用上の注意
-------------------
- DB 分離:
  - 監視系（monitoring）は settings.sqlite_path（デフォルト data/monitoring.db）を使用。
  - ペーパートレードは settings.paper_sqlite_path（デフォルト data/paper_trading.db）で本番 DB と分離。
- process priority / CPU affinity:
  - 起動スクリプトは psutil を使ってプロセス優先度を上げます（管理者権限が必要な場合があります）。
- LLM 呼び出し:
  - OPENAI_API_KEY を .env に設定するか引数で渡してください。
  - API のレート制限やネットワークエラーに対してはリトライ・フォールバック処理を備えていますが、コストと実行時間を考慮してください。
- .env 管理:
  - .env は秘匿情報を含むため Git 管理しないでください（config_setup も README にコメントを出力します）。
- ログディレクトリが作成できない場合はコンソール出力にフォールバックします（ファイル出力失敗時に警告が出る設計）。

よく使うコマンドまとめ
---------------------
- .env を生成/編集: python -m kabusys.config_setup
- 設定を検証:         python -m kabusys.validate_config [--strict]
- Execution 起動:     python -m kabusys.run_execution
- Monitoring 起動:    python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレードレポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアやレジーム判定は研究・運用スクリプト内から関数を呼び出す形で利用

この README はコードベースの主要ポイントを整理したものです。実運用やテスト目的でさらに詳しい手順（デプロイ手順、service/systemd ユニット、CI 設定、依存パッケージバージョン固定等）が必要な場合は、追加でその内容を詰めていきましょう。