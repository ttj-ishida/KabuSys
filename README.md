KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株自動売買システム「KabuSys」のコア部品群（設定管理、実行エンジン起動スクリプト、監視、ポートフォリオ構築、リサーチ、AI ニュース評価など）を含みます。本書は開発者向けの README で、プロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
----------------
KabuSys は以下のような役割を持つモジュール群で構成された自動売買基盤です。

- 実行エンジン（ExecutionEngine）: 発注ロジック・注文管理・リスク管理を実行する。
- 監視（Monitoring）: システム稼働状況、注文/約定の監視、ドローダウン監視、Kill Switch を提供。
- ポートフォリオ構築（Portfolio）: 銘柄選定、重み付け、ロット丸め、リスク制約の適用。
- リサーチ（Research）: DuckDB を利用したファクター計算・特徴量解析。
- AI モジュール（ai）: ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI API を利用）。
- ユーティリティ: ロギング設定、プロセス優先度、設定ウィザード、設定検証ツール等。
- ツール: Paper Trading の検証レポート等。

主な機能一覧
-------------
- 設定管理
  - .env 自動ロード / 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Settings クラスによる環境変数ラッパー（デフォルト値や検証を含む）
- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper DB に格納）
  - PID ファイル管理、stop フラグ検知による安全停止
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System/Trade/Risk 各モニタの統合、KillSwitch 評価、通知トリガー
  - MonitoringDB: SQLite に監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を永続化
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングし ai_scores に保存（news_nlp）
  - マクロニュース + ETF ma200 乖離を合成して市場レジーム判定（regime_detector）
  - API 呼び出しは堅牢にリトライ・バリデーション処理あり
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

前提・依存関係
---------------
最低限必要なもの（サンプル、環境に応じて調整してください）:

- Python 3.10+
- pip でのインストール例:
  pip install duckdb psutil openai
- オプション:
  - PyYAML（validate_config の YAML 検証に使用）
- DB:
  - sqlite3（Python 標準）
  - DuckDB（duckdb パッケージ）

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリに移動:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
   pip install duckdb psutil openai
   （開発用に requirements.txt があれば pip install -r requirements.txt を使用）

4. .env の作成（対話式ウィザード推奨）:
   python -m kabusys.config_setup
   ウィザードは .env（デフォルト）を生成/更新します。機密値はシークレット入力になります。

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY （AI 機能を使う場合、news_nlp/regime_detector で必要）
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - DUCKDB_PATH （デフォルト data/kabusys.duckdb）
   - SQLITE_PATH （監視 DB, デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH （paper_trading 用 DB, デフォルト data/paper_trading.db）
   - LOG_LEVEL, LOG_DIR など
   - PAPER_FILL_MODE (paper_trading の MockBroker の挙動: instant|partial|never|reject)

5. 設定検証（推奨）:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗として扱います。

6. データディレクトリ等の準備:
   デフォルトで logs/ や data/ を作成しますが、.env のパスを確認して必要ならディレクトリを作成してください。

使い方
-------
起動・実行に関する主要コマンド例は以下の通りです。パッケージをインストール済みで、.env が正しく設定されていることを前提とします。

- 実行エンジンを起動（メインプロセス）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag があれば起動せず終了します。
  - 実行中に data/stop_requested.flag を作成すると Engine を停止します。
  - 起動時に PID は data/execution.pid（デフォルト）に書き込まれます（設定で変更可）。

- 監視ループを起動:
  python -m kabusys.run_monitoring
  - デフォルトは MONITOR_POLL_INTERVAL=60 秒でポーリング。
  - 環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - run_monitoring は Settings.env にかかわらず production（本番）用 sqlite_path を使用します（監視は本番 DB を参照）。

- Paper Trading 検証レポートの生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（プログラムから呼び出し）:
  - news_nlp.score_news(conn, target_date, api_key=None)  # api_key 指定なしなら OPENAI_API_KEY を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  OpenAI API キーが必要です（OPENAI_API_KEY）。

停止・Kill/Stop フラグ
- run_* スクリプトはプロジェクトの data/stop_requested.flag を監視しています（スクリプト内の _STOP_FLAG）。このファイルを作成するとポーリングループは次サイクルで優雅に終了します。
- KillSwitch（監視側）は data/kill.flag を書き込み、ExecutionEngine に「停止すべき」旨を通知します（Execution 側は Settings.kill_flag_path を参照して処理）。
- kill.flag を手動でクリアするにはファイルを削除してください（設定により起動時に自動クリアするオプションあり：KILL_FLAG_CLEAR_ON_START）。

ログ
- ログはデフォルトで logs/ フォルダに出力されます（アプリ名毎にファイル: execution.log, monitoring.log 等）。
- ログレベルは .env の LOG_LEVEL または setup_logging の引数で制御可能。
- ローテーションは日次で 30 日分保持。

ディレクトリ構成（主なファイルと説明）
-----------------------------------
以下はプロジェクトの主要なモジュール構成（src/kabusys 以下）。実ファイルは一部抜粋しています。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"

  - run_execution.py
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper DB を使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可。

  - config.py
    - Settings クラス、.env 自動ロード、環境変数パースロジック。

  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）。

  - validate_config.py
    - 起動前の設定検証 CLI（python -m kabusys.validate_config）。

  - utils/
    - logging_setup.py — ルートロガー設定（コンソール + 日次ファイルローテーション）
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化（テーブル定義・MonitoringDB クラス）
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / Execution プロセス監視
    - trade_monitor.py — (trade 関連監視: 滞留注文、約定異常など) — （ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み・評価
    - alert_manager.py — 通知管理（LINE 等への通知を想定）
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ

  - execution/
    - execution_engine.py — 実行エンジンコア
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - （発注ロジック・リスク判定・ブローカ抽象化）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注数量計算・集約上限処理
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py

  - ai/
    - news_nlp.py — ニュースを LLM でセンチメントスコアリングして ai_scores に書き込む
    - regime_detector.py — ETF ma200 + マクロニュースで市場レジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
    - __init__.py

補足・運用上の注意
-----------------
- run_monitoring は監視専用 DB（Settings.sqlite_path）を使用します。run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用します（本番 DB と混在しない）。
- AI 機能を利用する際は OpenAI API キーを必ず設定してください（OPENAI_API_KEY）。API 呼び出しはリトライやレスポンス検証を行いますが、API コストとレイテンシに注意してください。
- .env は機密情報を含むため Git にコミットしないでください（config_setup の注意書きに従ってください）。
- validate_config で事前チェックを推奨します。特に KABUSYS_ENV=live の場合は注意喚起が表示されます。
- ローカルテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い .env の自動ロードを無効化できます。

ライセンス・貢献
----------------
（リポジトリに LICENSE があればここに記載してください。プロジェクト固有の貢献ガイドラインがあれば追記してください。）

お問い合わせ
------------
何か不明点や改善提案があれば、リポジトリの Issues またはコードオーナーへご連絡ください。

以上。README に追記してほしい情報（例えば実際の起動オプション詳細や環境別運用手順など）があれば教えてください。必要に応じてサンプル .env.example を生成する手順も追加できます。