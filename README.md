KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システムの一部実装（設定・監視・発注エンジン・研究ツール等）を含みます。  
以下はコードベースに基づく日本語の README（概要、機能、セットアップ手順、使い方、ディレクトリ構成）です。

プロジェクト概要
--------------
KabuSys は日本株自動売買のためのモジュール群です。主な責務は次の通りです。

- 発注エンジン（ExecutionEngine）による注文管理とリスク管理
- 監視（Monitoring）: システム稼働状況・注文の健全性・リスク監視と Kill Switch
- ポートフォリオ構築・ポジションサイジング（Portfolio）
- リサーチ（Research）: ファクター計算・特徴量探索
- AI 補助（AI）: ニュース NLP によるセンチメント評価・レジーム判定
- ユーティリティ（設定管理、ロギング、プロセス優先度など）
- 開発・運用向けツール（環境設定ウィザード、設定検証、Paper Trading レポート）

主な特徴（機能一覧）
-----------------
- 設定管理
  - .env の対話式作成・更新ウィザード（kabusys.config_setup）
  - 起動前の設定/ファイル検証 CLI（kabusys.validate_config）
  - 自動 .env 読み込み（OS 環境変数 > .env.local > .env。無効化オプションあり）
- 発注/実行
  - 実行環境に応じたブローカー選択（本番 / ペーパートレード分離）
  - ペーパートレード用専用 SQLite（デフォルト: data/paper_trading.db）
  - PID ファイル / stop フラグ検知による安全停止
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセスの死活を監視
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager を組み合わせた監視エンジン
  - 監視結果は SQLite（data/monitoring.db）へ永続化
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重、リスクに基づくポジションサイズ計算
  - セクター上限やレジーム乗数の適用ロジック
- リサーチ
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）等の統計ツール
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - 市場レジーム判定（ETF 指標 + マクロニュースの LLM 評価の融合）
  - API 呼び出しのリトライやレスポンス検証を含む堅牢な実装
- 運用ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）
  - ログは日次ローテーションでファイル保存（logs/<app_name>.log）と標準出力

動作環境・前提
-------------
- Python 3.10 以上（型注釈で | 記法を使用）
- 必須 Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml のパース検証用）
- SQLite（組み込み）を使用
- 環境変数による設定を多用（.env ファイルを推奨）

セットアップ手順
--------------
1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成し有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 開発用に PyYAML を検証したければ: pip install pyyaml
   - （プロジェクトに requirements.txt があればそれを使用）
4. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードが生成する .env は data/、ログ等のパスや API キーを含みます
5. 設定検証（起動前に必ず実行推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます
6. data ディレクトリ等の作成（通常はコードが自動作成します）
7. 環境変数の注意点
   - 自動 .env 読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - よく使う変数:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
     - DUCKDB_PATH（default: data/kabusys.duckdb）
     - SQLITE_PATH（default: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時のデータベース）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR

使い方（起動・コマンド例）
-----------------------

- 実行エンジン（ExecutionEngine）を起動
  - 簡単起動:
    - KABUSYS_ENV=development python -m kabusys.run_execution
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 注意: 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - PID は data/execution.pid（デフォルト）に書き込まれます

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path / data/monitoring.db）を使います（環境に依存せず監視 DB は共通）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証ツール
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（標準出力に表示）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（オプション）:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH も使用可能

- AI / リサーチ機能（ライブラリ的に呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")
  - DuckDB 接続を渡して関数を呼び出す形式です（コマンドラインスクリプトは用意されていません）

運用メモ / 重要な挙動
--------------------
- DB の分離
  - 監視は常に Settings.sqlite_path（監視 DB）を使用
  - 実行エンジンは KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と完全分離
- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止を促します
  - ExecutionEngine は data/stop_requested.flag を検知すると安全に停止します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では 0 推奨）
- ログ
  - setup_logging() により logs/<app_name>.log を日次ローテーションで保存（デフォルト logs ディレクトリ）
  - コンソール出力は stdout（cron 等で stdout をリダイレクトしやすくするため）
- プロセス優先度 / CPU affinity
  - set_process_priority() / set_cpu_affinity() が用意されています（psutil を利用）
  - 権限が不足している場合は警告を出してスキップします
- .env 自動読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）を自動探索し .env/.env.local を読み込みます
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定ファイル（.env）に含める代表的な変数
----------------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN=your_token
  - KABU_API_PASSWORD=your_password
- 推奨 / 主要:
  - KABUSYS_ENV=development|paper_trading|live
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - OPENAI_API_KEY=sk-...
  - LOG_LEVEL=INFO
  - LOG_DIR=logs
  - KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主なファイル）
------------------------------
※ 実際のパッケージルートは src/kabusys/ 以下にある想定です。以下は主要なサブモジュールと代表ファイルの一覧です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env 読み込みを含む）
  - config_setup.py          — .env 対話式ウィザード（CLI）
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

  - execution/               — 発注エンジン関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化・アクセス層
    - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（滞留注文、約定異常等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等）※実装箇所あり
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・aggregate cap
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summary 等
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 呼び出し、スコア DB 書込み）
    - regime_detector.py     — 市場レジーム判定（ETF MA + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

補足（開発者向け）
-----------------
- DuckDB は分析・研究用の高速クエリエンジンとして用いられ、prices_daily / raw_financials / raw_news 等のテーブルを前提とします
- AI 関連は OpenAI の Chat Completions（JSON mode）を想定。OPENAI_API_KEY の管理は .env / 環境変数を推奨
- テスト用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の自動ロードを無効化できます
- monitoring_db.init_monitoring_db() は冪等にスキーマを作成し、簡単なマイグレーション処理を含みます

よくある運用フロー（例）
---------------------
1. 初期セットアップ:
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config
2. データ準備（DuckDB に prices_daily, raw_financials, raw_news などを投入）
3. 監視サービス起動:
   - python -m kabusys.run_monitoring
4. 発注エンジン起動（本番 / ペーパートレード切替）:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. 定期的に Paper Trading レポートの出力や AI スコアリングを実行して検証・分析

ライセンス・貢献
----------------
（ここではコードベースにライセンスが含まれていないため、プロジェクトポリシーに合わせて追記してください）

おわりに
-------
この README は提供されたコードベースを基にまとめたものです。実運用時は各 config/*.yaml、環境変数、接続先情報、API キーの管理、ログ/監視設定を慎重に行ってください。追加のドキュメント（設計ノート / 操作手順）はプロジェクト固有の運用ルールに沿って整備することを推奨します。