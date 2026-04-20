KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）起動スクリプト（発注・リスク管理などの実行）
- 監視コンポーネント（MonitoringEngine）によるシステム/取引/リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI ユーティリティ（ニュースセンチメント解析 / 市場レジーム判定）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度制御、DB 初期化 等）
- 運用用スクリプト（.env ウィザード、設定検証、ペーパートレード検証レポート）

特徴
----
- 環境変数 / .env による設定管理（config_setup による対話式生成）
- KABUSYS_ENV による環境切替（development / paper_trading / live）
  - paper_trading 時は mock ブローカーを用い、paper 用 DB に記録して本番 DB と分離
- SQLite（監視・注文ログ等）と DuckDB（分析用テーブル）を併用
- ログはコンソール + 日次ローテーションファイル（logs/<app>.log）で管理
- OpenAI を使ったニュース NLP / レジーム判定をサポート（API 呼出しは任意）
- Kill Switch（data/kill.flag） による外部からの緊急停止機構
- stop フラグ（data/stop_requested.flag）でプロセスを安全に終了可能

セットアップ
----------
1. Python 環境
   - 推奨: Python 3.10+（コードは型注釈を多用しています）
2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（validate_config が YAML のパース検証を行う場合）
   - 例: pip install -r requirements.txt
     （requirements.txt がない場合は上記パッケージを個別にインストールしてください）
3. プロジェクトルートに移動して .env を準備
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 生成後、設定の検証:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict  # 警告も失敗扱い
4. デフォルト DB / ディレクトリ
   - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
   - SQLite (監視): data/monitoring.db（環境変数 SQLITE_PATH）
   - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
   - logs/ ディレクトリは自動作成されます（書き込み権限を確認）

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API パスワード
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

使い方
------

起動スクリプト（運用）
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 概要: SystemMonitor を初期化し、定期的に監視処理を実行して monitoring DB に記録します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成すると検知して終了します。

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 概要: ブローカークライアントを生成し ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に stop フラグを置くと安全に停止を試みます。

設定関連 CLI
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成 / 更新を対話式で行います（--env-file でパス指定可）

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - .env と config/*.yaml の整合性チェック、重要な環境変数の有無や DB パスの親ディレクトリの確認などを行います。

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定できます。
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等の集計と PASS/FAIL 判定

プログラム API（主な関数）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - raw_news を集約して OpenAI でセンチメントを算出し ai_scores テーブルへ書き込みます。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF の MA200 と LLM マクロセンチメントを合成して market_regime に書き込みます。
- kabusys.portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

運用上の注意
-----------
- kill.flag / stop flag
  - data/kill.flag: KillSwitch によって書き込まれる緊急停止フラグ。ExecutionEngine はこのフラグを監視して停止します。
  - data/stop_requested.flag: run_monitoring/run_execution が参照する「プロセス停止リクエスト」フラグ。運用者が作成することで安全にループを抜けます。
- ログ: logs/<app>.log に日次でローテート（30 日保管）。ログディレクトリに書き込み可能か確認してください。
- Paper Trading: KABUSYS_ENV=paper_trading 時は本番 DB とは完全に分離されます。テスト時は必ずこのモードを使用してください。
- OpenAI の API 呼び出しは課金対象です。API キーの管理に注意してください。API 呼び出しに失敗した場合はフェイルセーフ（スコア 0.0 等）で継続する設計です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数／設定読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — 監視ループ起動スクリプト
- run_execution.py         — 実行エンジン起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py     — 市場レジーム判定（MA200 + LLM）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・リスク制限・単元丸め
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- monitoring/
  - monitoring_db.py       — SQLite スキーマ初期化と永続化 API
  - system_monitor.py      — システム / データ鮮度監視
  - trade_monitor.py       — （trade 監視ロジック、ファイル中の実装参照）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — Kill Switch 実装
  - monitoring_engine.py   — 各モニタ束ねるエンジン
  - alert_manager.py       — （アラート送信ロジック、ファイル参照）
- execution/
  - execution_engine.py    — ExecutionEngine（起動・セッション管理）
  - order_manager.py       — 発注管理
  - order_repository.py    — 注文永続化
  - reconciler.py          — オーダー状態整合
  - broker_factory.py      — BrokerClient の生成（本番 / mock）
  - risk_manager.py        — リスクチェック（rate limit 等）
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート

補足
----
- YAML 検証: validate_config は PyYAML がある場合に config/*.yaml をパースして検証します。未インストールでも実行は可能ですが YAML の内容チェックをスキップします。
- テスト/開発時に自動で .env を読み込みたくない場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます。
- 実装の詳細やアルゴリズム（ポートフォリオ設計やストップロス算出等）はソースコード内のドキュメントコメントを参照してください。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報は本リポジトリの LICENSE（存在する場合）を参照してください。

問い合わせ / 開発メモ
--------------------
- 開発者向け: 各モジュールはドキュメンテーション文字列（docstring）を充実させています。具体的な振る舞いや引数/戻り値は該当ソースを参照してください。
- 本 README に含めてほしい追加情報（例: デプロイ手順、systemd ユニット例、docker-compose など）があれば教えてください。