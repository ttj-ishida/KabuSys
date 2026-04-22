KabuSys — 日本株自動売買フレームワーク
====================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のミニマル実装です。  
主な目的は次のとおりです。

- データ収集・分析（DuckDB ベースの価格データ参照）
- ファクター計算・特徴量解析（research）
- ポートフォリオ構築（候補選定・配分・ポジションサイズ）
- 発注実行エンジン（paper_trading と live を切り替え可能）
- 監視・アラート（監視 DB にログ、Kill Switch による停止）
- AI 補助（OpenAI を用いたニュース NLP / レジーム判定）
- ペーパートレード検証レポート生成ツール

本リポジトリはモジュール群（execution / monitoring / research / portfolio / ai / utils 等）に分かれており、軽量な CLI スクリプトで起動・検証・設定ウィザードが利用できます。

主な機能一覧
--------------
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）および対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV に応じた Broker クライアント（paper_trading のときは MockBroker）
  - リスク管理、オーダー管理、再整合（reconciler）等の組み込み
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite：data/monitoring.db）
  - Kill Switch による自動停止（data/kill.flag）
  - run_monitoring ポーリングループ（MONITOR_POLL_INTERVAL で間隔調整）
- ポートフォリオ構築
  - 候補選定、等分/スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を直接使用）
  - 将来リターン計算、IC（スピアマン）等の統計ツール
- AI（OpenAI）
  - ニュース集約 → LLM でセンチメントスコアを生成し ai_scores テーブルへ書込む
  - マクロニュース x ETF MA200 乖離を用いた市場レジーム判定
- ツール
  - Paper Trading の検証レポート出力スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------
前提
- Python 3.9+（ソースは typing, match 等を使わないため 3.9 以上を想定）
- SQLite（標準ライブラリで利用可）
- DuckDB、psutil、openai 等の Python パッケージ

推奨手順
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - オプション: PyYAML を入れると validate_config の YAML 検証が有効化されます
     - pip install pyyaml

   （プロジェクトに requirements.txt が無い場合は上記で充分です）

3. .env の作成
   - 対話式ウィザード（推奨）
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（プロジェクトルートに置く）
     - 例（最小）:
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_kabu_password
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従って修正。--strict を付けると警告も失敗扱いになります。

ファイル・ディレクトリ（自動生成）
- data/ — SQLite や PID / flag ファイルが配置される想定ディレクトリ
  - data/monitoring.db (デフォルト)
  - data/paper_trading.db (paper_trading 時の専用 DB)
  - data/kabusys.duckdb (分析用 DuckDB)
  - data/execution.pid, data/stop_requested.flag, data/kill.flag
- logs/ — ログ出力（setup_logging により自動生成）

使い方（主要コマンド）
---------------------

1) 実行エンジンを起動
- 本番/ペーパーを切り替える:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live         python -m kabusys.run_execution
  - もしくは .env に KABUSYS_ENV を設定して単に:
    python -m kabusys.run_execution

- 停止:
  - 実行エンジンはプロセス優先度を上げ、data/stop_requested.flag の存在を確認して終了します。
  - Kill Switch（監視側）がトリガーすると data/kill.flag を書き込んでエンジン停止を促します。

2) 監視ループを起動
- python -m kabusys.run_monitoring
- ポーリング間隔を変更する場合:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3) 設定ウィザード
- python -m kabusys.config_setup
  - .env を対話式に作成／更新します。

4) 設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も EXIT 1（失敗）になります。

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パス指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

6) AI スコア・レジーム判定（ライブラリ呼び出し例）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定しておく
- ニュース NLP:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)

主な環境変数
---------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live) — default: development
- OPENAI_API_KEY — AI 機能利用時に必須
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB のデフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)

ディレクトリ構成（主なファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証ツール
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリング起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書込
  - regime_detector.py      — マクロ + ETF MA200 を合成してレジーム判定
- monitoring/
  - monitoring_db.py        — SQLite を使った監視ログ永続化層
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — (注文周りの監視: ファイル内に存在)
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag の作成・管理
  - monitoring_engine.py    — 各モニタの束ね・Polling ループ
  - alert_manager.py        — （アラート送信管理）
- execution/
  - execution_engine.py     — エンジン本体（セッション管理）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/
  - pipeline.py (DuckDB / price helpers 等)
  - stats.py (zscore_normalize 等)
- utils/
  - logging_setup.py        — 共通ロギング設定
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py

運用上の注意
-------------
- KABUSYS_ENV=live の場合は実際に発注が行われます。本番稼働前に必ず validate_config の結果と .env の値を確認してください。
- .env は決してリポジトリにコミットしないでください（config_setup のヘッダにも警告あり）。
- OpenAI API 呼び出しはコストとレイテンシが発生します。rate-limit / エラー対策はコード内に実装されていますが、API キーの管理と利用ポリシーの確認を行ってください。
- 監視側は data/stop_requested.flag を監視して安全にシャットダウンできます。手動停止する場合はこのファイルを作成してください。
- デフォルトの DB パス（data/ 以下）は環境・運用要件に合わせてお使いください。

開発者向けメモ
----------------
- ログ: kabusys.utils.logging_setup.setup_logging を各起動スクリプト最初に呼び出すことで標準化されたログ管理が利用できます。
- プロセス優先度: utils/process_priority.set_process_priority("high") を使ってOSごとの優先度設定を行っています（権限によっては失敗し警告が出ます）。
- DuckDB を利用したファクター計算は外部依存を減らすため SQL と純 Python で記述されています（pandas 非依存）。
- テスト時には OpenAI など外部 API 呼び出し箇所を unittest.mock.patch 等で差し替えてください。

ライセンス・バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンスは本リポジトリには明示されていません。配布・利用時はプロジェクトのライセンス方針を明確にしてください。

お問い合わせ・貢献
-----------------
バグ報告や改善提案・プルリクエストはリポジトリの Issues / PR を利用してください。README に含めてほしい追加情報や使い方の例があれば教えてください。