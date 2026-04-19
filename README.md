KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買・研究・監視機能を備えた内部ライブラリ群です。  
README はプロジェクト概要、機能、セットアップ手順、使い方（起動コマンド例）およびディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は以下を目的としたモジュール群を提供します。

- 戦略の研究（ファクター計算、特徴量解析）
- ポートフォリオ構築（銘柄選定・ウェイト計算・株数算出）
- 実行エンジン（ExecutionEngine）による発注管理（本番 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk）および Kill Switch（異常時自動停止）
- ニュース NLP（OpenAI を用いたセンチメント評価）やレジーム判定
- ユーティリティ（設定ウィザード、設定検証、ログ設定など）
- レポート作成ツール（Paper Trading 検証レポート等）

主な設計方針：
- DB（DuckDB / SQLite）を用いたデータ永続化・分析
- 本番 / ペーパートレードの明確な分離（paper_trading 環境で専用 DB を使用）
- ルックアヘッドバイアス回避（日時参照は呼び出し側から受け取る等）
- フェイルセーフ（API 失敗時はスキップまたは安全なデフォルトで継続）

機能一覧
--------
主な機能（抜粋）:

- 設定管理
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading: MockBrokerClient を使用し data/paper_trading.db に記録

- 監視
  - System / Trade / Risk モニタリング
  - MonitoringEngine（ポーリングループ）
  - Kill Switch（条件により data/kill.flag を書き込んで ExecutionEngine を停止）
  - run_monitoring.py：ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）

- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスク調整（セクター上限）、株数決定（単元丸め）

- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI / NLP
  - ニュースセンチメント（OpenAI を使用）
  - 市場レジーム判定（MA + マクロセンチメントの合成）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python 環境準備（推奨）
   - Python 3.10+ 推奨（typing の記法等に依存）
   - 仮想環境作成例：
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - requirements.txt は含まれていない想定のため主要依存例：
     - pip install duckdb psutil openai
     - PyYAML は設定ファイル検証で任意：pip install pyyaml
   - 実行環境に合わせて追加パッケージを導入してください。

3. .env の作成
   - 対話式ウィザードで初期 .env を作成：
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合：
     - OPENAI_API_KEY を環境変数に設定（または各関数呼び出しで引数に渡す）
   - その他の主要環境変数（デフォルトあり）：
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL（default: INFO）
     - KILL_FLAG_CLEAR_ON_START（0/1）
   - 自動読み込みはデフォルトで有効（プロジェクトルートの .env / .env.local）。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. データディレクトリ
   - デフォルトで data/、logs/ を使用します。起動スクリプトが存在しない場合は自動作成しますが、権限に注意してください。

使い方（起動 / CLI）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番DBと分離）
    - 実行中は data/execution.pid を利用
    - 停止方法: data/stop_requested.flag を作成すると実行ループが検知して停止
    - Kill Switch（data/kill.flag）を監視して外部から強制停止させる運用も可能

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 注意: monitoring 用の SQLite（監視ログ）は KABUSYS_ENV に関わらず Settings.sqlite_path（本番パス）を使用します
  - 停止方法: data/stop_requested.flag

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db / 環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）

- AI / NLP 機能
  - kabusys.ai.score_news などは OpenAI API キーが必須（引数で渡すか OPENAI_API_KEY を設定）
  - レート制限や一時的障害に対してリトライ・フェイルセーフを実装済み

- ロギング
  - setup_logging が各起動スクリプトから呼ばれ、logs/<app_name>.log に日次ローテーションで出力します
  - LOG_DIR 環境変数でログディレクトリを変更可能

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では .env の値、LINE 通知（LINE_CHANNEL_ACCESS_TOKEN/LINE_USER_ID）等を十分に確認してください。
- KILL_FLAG_CLEAR_ON_START=1 を本番で使用すると危険（Kill Switch が自動でクリアされるため）。
- run_monitoring は監視専用 DB パスを使用するため、意図せず本番 DB を上書かないよう環境変数を確認してください。
- OpenAI を利用する機能は API 利用料がかかります。バッチサイズや呼び出し頻度を運用に合わせて調整してください。

ディレクトリ構成
----------------
主要ファイル・ディレクトリ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - utils/
    - __init__.py
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

  - execution/
    - broker_factory.py       — Broker クライアント生成（Mock / 実ブローカー）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定

  - data/                     — 実行時に使われる既定の保存先（example）
    - monitoring.db (デフォルト: SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid などのフラグファイル

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート

よくある操作例（まとめ）
-----------------------
- .env を作る（対話式）:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（デフォルト 60 秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ペーパートレード）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper Trading レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

補足（開発者向け）
------------------
- DuckDB 接続を受ける研究系関数は副作用を持たず、テストしやすい純粋関数群として設計されています。
- API 呼び出し部（OpenAI）やプロセス優先度設定（psutil）などはテスト時にモック可能な形で実装されています。
- SQLite / DuckDB のスキーマ更新（マイグレーション）は簡易なチェック + ALTER を用いて実行時に互換性確保を行います。

ライセンス・バージョン
--------------------
- パッケージバージョン（内部）: __version__ = "0.1.0"
- ライセンス情報は別途 LICENSE ファイルを参照してください（本リポジトリに含めてください）。

問い合わせ / 貢献
-----------------
- バグ報告・機能提案は issue を作成してください。
- 小さな修正や追加機能はプルリクエスト歓迎です。テスト・ドキュメントを添えてください。

以上がこのコードベースの README 相当の説明です。必要であれば README.md の具体的なテンプレート（ファイル内容）を作成します。どの形式（短縮版 / 詳細版）を希望しますか？