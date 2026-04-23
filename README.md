KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買フレームワーク「KabuSys」のコードベースです。
主要機能はシグナル生成、ポートフォリオ構築、発注実行、監視、Paper Trading 用検証、そして AI を使ったニュースセンチメント判定などです。

以下は本リポジトリの README（日本語）です。セットアップ手順・使い方・ディレクトリ構成などをまとめています。

プロジェクト概要
----------------
- 名前: KabuSys
- 目的: 日本株を対象とした自動売買システムの基盤ライブラリおよび実行スクリプト群
- 主な責務:
  - 戦略（ファクター計算、特徴量解析）
  - ポートフォリオ構築（候補選定・重み計算・株数決定）
  - 発注実行エンジン（本番 / ペーパートレード切替）
  - 監視（システム状態、注文/約定、リスク監視、Kill Switch）
  - AI モジュール（ニュース NLP によるセンチメント・レジーム判定）
  - ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証など）
- ライセンス・バージョン等: __version__ = "0.1.0"（src/kabusys/__init__.py）

主な機能一覧
-------------
- 環境設定管理
  - .env 自動ロード（.env / .env.local）と Settings クラス（src/kabusys/config.py）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行エンジン
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - 本番 / paper_trading の切替（KABUSYS_ENV）
  - paper_trading 時は MockBrokerClient を用い、data/paper_trading.db に記録

- 監視（Monitoring）
  - System / Trade / Risk モニタの集合体（MonitoringEngine）
  - run_monitoring スクリプト: src/kabusys/run_monitoring.py（MONITOR_POLL_INTERVAL で間隔変更可）
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - 監視ログ永続化（SQLite）と簡易 DB マイグレーション処理

- ポートフォリオ構築
  - 候補選定（score/順位）・等金額/スコア重みの計算
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイジング（単元株丸め、リスクベース配分、aggregate cap）

- 研究・分析
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリ等（研究用ユーティリティ）

- AI（OpenAI）連携
  - ニュースセンチメント: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
  - OpenAI API（gpt-4o-mini）を使用（APIキーは環境変数 OPENAI_API_KEY）

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10+（使用ライブラリの互換性に合わせてください）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - このリポジトリに requirements.txt は含めていません。少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 初期 .env 作成（対話式）
   - python -m kabusys.config_setup
   - ウィザードに従って必須の環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を設定
   - 生成後、python -m kabusys.validate_config で検証

5. ディレクトリ作成（必要に応じて）
   - デフォルト DB / ログパスは data/ と logs/（設定で変更可）に書き込みます。
   - 例: mkdir -p data logs

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（ニュース NLP / レジーム判定時に必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO、DEBUG）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数。デフォルト 60）
- PAPER_FILL_MODE（paper_trading 時の fill 動作: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア制御。1でクリア）

基本的な使い方
-------------
- .env を作成・編集
  - python -m kabusys.config_setup
  - 生成後、環境変数を反映（シェルで export / Windows では set）

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 監視（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（例: MONITOR_POLL_INTERVAL=30）
  - 仕様: 停止にはプロジェクトルート/data/stop_requested.flag を作成する（run_monitoring はこの存在を検知して終了）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB を使用し、MockBrokerClient を利用（本番 DB と分離）
  - 実行停止は同じく data/stop_requested.flag を作成するとエンジンに通知されて終了処理される

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能を使う（プログラムから）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...)  # DuckDB 接続を渡す

- ログ設定
  - 各起動スクリプトは最初に setup_logging(app_name=...) を呼び出します。
  - デフォルトで stdout と logs/<app_name>.log に日次ローテートで出力（logs/ ディレクトリ）

停止・Kill Switch
-----------------
- Kill Switch は監視コンポーネントがリスクルール（ドローダウン等）を検出したときに data/kill.flag を作成します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 をセットしていると自動で clear される設定になり得ますが、本番では 0 を推奨します。
- 手動で停止する場合はプロジェクトルート/data/stop_requested.flag を作成してください（run_* スクリプトはこれを検知して終了します）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 内の主要モジュールと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — Settings クラス（環境変数 / .env 自動ロード / validation helpers）
  - config_setup.py — .env 作成の対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI でセンチメント付与）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・aggregate cap
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility ファクター
    - feature_exploration.py — 将来リターン / IC /統計
  - monitoring/
    - monitoring_db.py — SQLite 永続化 API（init / read/write）
    - system_monitor.py — CPU/MEM/DISK/データ鮮度監視
    - trade_monitor.py — (参照: 注文滞留/約定異常）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - monitoring_engine.py — 全モニタ束ね処理
    - alert_manager.py — (参照: アラート送信機能)
  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ （実行時に使うファイル）
    - monitoring.db（デフォルト）
    - kabusys.duckdb（デフォルト）
    - paper_trading.db（paper_trading 用）
    - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

補足／開発者向けメモ
-------------------
- DB マイグレーション: monitoring_db.init_monitoring_db() はテーブル作成だけでなく、既存 DB に列がなければ ALTER TABLE を行う簡易マイグレーションを実施します。
- ロギング: setup_logging は既存ハンドラをクリアして再設定するため、スクリプトから複数回呼ぶ際の二重出力を防止します。
- プロセス優先度: run_* スクリプトは起動時に set_process_priority("high") を呼びます（psutil を利用）。
- Paper Trading: KABUSYS_ENV=paper_trading にすると paper_trading 用 SQLite を使用し、実際の発注は行われません（MockBrokerClient を使用）。
- AI 呼び出し: OpenAI API を使う箇所はリトライ・バックオフ・JSON バリデーションなどを実装しており、API失敗時は安全側フォールバックする設計です（例: macro_sentiment=0.0）。

よくある操作コマンド例
---------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問題報告・拡張
--------------
- 機能追加／バグ修正は Issue を立ててください。設計上、各機能はモジュール分割されておりユニットテストが書きやすくなっています。
- 将来的な拡張候補:
  - 銘柄単位の lot_size 拡張（stocks マスタとの連携）
  - 監視アラートのプラグイン化（Slack / PagerDuty / LINE 等）
  - DuckDB による分析パイプラインの強化（ETL スケジューリング）

最後に
------
この README は現行ソース（src/kabusys 配下）を基に作成しています。初期セットアップや運用に関しては、.env.example（存在する場合）や config/*.yaml（生成スクリプトあり）を参照してください。質問や追加説明が必要であれば教えてください。