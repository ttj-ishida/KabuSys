README
======

概要
----
KabuSys は日本株向けの自動売買支援ライブラリ / 実行環境です。本リポジトリは以下の主要機能を持ちます:

- 発注エンジン（ExecutionEngine）の起動スクリプトと周辺コンポーネント
- 監視機能（System / Trade / Risk）と Kill Switch（自動停止）機構
- ポートフォリオ構築（候補選定・重み付け・株数決定）ユーティリティ
- リサーチ用ファクター計算・特徴量解析モジュール（DuckDB を利用）
- ニュース NLP による銘柄センチメント（OpenAI を利用）およびレジーム判定
- Paper Trading 向け分離 DB、検証レポート生成ツール
- .env 対話式ウィザード・設定検証 CLI、統一的なログ設定ユーティリティ

本 README は開発者 / 運用者がセットアップして起動するための手順と各コンポーネントの説明をまとめたものです。

主な機能
--------
- ExecutionEngine 起動（run_execution.py）
  - KABUSYS_ENV により paper_trading モードでの MockBrokerClient 利用や本番モードを切替
  - paper_trading は data/paper_trading.db（デフォルト）を使用して本番 DB と分離
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム資源、データ鮮度、注文状況、リスク（ドローダウン・ポジション上限）を定期監視
  - Kill Switch による停止判定と flag ファイル書き込み
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）、株数決定（lot 丸め）
- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC 計算、統計サマリー
  - DuckDB を用いて prices_daily / raw_financials 等のテーブルから計算
- AI（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースのセンチメント算出と ai_scores への書き込み
  - regime_detector: ma200 乖離 と マクロニュースセンチメントの合成による市場レジーム判定
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

前提 / 要件
-----------
- Python 3.10+（typing の | 演算子等を使用）
- 推奨パッケージ（プロジェクトに応じてインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を使う場合）
- SQLite は標準ライブラリで利用可能
- 実際に kabuステーション や J-Quants 等の API を使う場合は該当 API の認証情報が必要

セットアップ手順
----------------
1. リポジトリをクローンして仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストール（例）:
   - pip install duckdb psutil openai PyYAML
   - 実運用で使用する追加の broker クライアント等があれば合わせてインストールしてください。

3. 環境変数の準備（.env）:
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参考に）

4. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります:
     - python -m kabusys.validate_config --strict

5. 必要なディレクトリ（data, logs 等）は自動作成されますが、アクセス権等を確認してください。

主な環境変数
-------------
（代表的なものを抜粋）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード ("instant" | "partial" | "never" | "reject")
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（"0"/"1"）

使い方（起動例）
----------------

- .env を作成・編集
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ PAPER_TRADING_SQLITE_PATH に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag が作成されるとエンジンは順次停止します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用してログを残します（環境にかかわらず）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI スコアリング / レジーム判定（ライブラリ関数として利用）
  - Python 内から:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。
- setup_logging() が全起動スクリプトから使われており、コンソール（stdout）への出力も行います。
- ログ出力先ディレクトリは LOG_DIR 環境変数または setup_logging の引数で変更可能。

Kill Switch / 停止制御
---------------------
- Kill Switch はリスク条件（ドローダウンやポジション上限）を満たした場合に data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアします（本番では推奨しない）。
- 監視・実行のループ停止には data/stop_requested.flag ファイルを作成する方法もあります（運用用の強制停止フラグ）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
    - Settings クラス（.env と環境変数の読み込み・解決）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定チェック CLI
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite による永続化レイヤ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — 発注/約定の監視（ファイルには同名の実装あり）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイル運用による停止信号
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — 通知（LINE 等、実装は別ファイル）
  - execution/
    - execution_engine.py — 発注エンジン本体（外部参照）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行系サブコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定・上限・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム、ボラティリティ、バリュー計算
    - feature_exploration.py — forward returns, IC, summary
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント取得
    - regime_detector.py — ma200 とマクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - data/ (ランタイム生成)
    - monitoring.db（デフォルト） / paper_trading.db（ペーパートレード用）
    - execution.pid, kill.flag, stop_requested.flag などのフラグ/ファイル

設計上の注意点 / 運用メモ
------------------------
- Settings は .env を自動でプロジェクトルートから読み込みます（.git または pyproject.toml を基準）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- run_monitoring は監視用 DB に常に「本番 sqlite_path」を使用します（監視ログは本番 DB に記録される想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に完全分離して記録します。
- psutil によるプロセス優先度変更は OS / 権限に依存します。失敗時は警告に留まりエラーは吐きません。
- OpenAI を利用する機能は API の呼び出し制限（429 等）やネットワークエラーに対してリトライ実装が入っていますが、APIキー管理やコストに注意してください。

サポート / 変更
----------------
- README に記載のない実装詳細は各モジュール（上記ファイル）を参照してください。
- 設定項目やしきい値は config/*.yaml 等を用意する設計になっています（validate_config がチェックします）。必要に応じて設定ファイルを生成・編集してください。

以上。運用開始前に必ず python -m kabusys.validate_config で設定チェックを行い、監視とログが正常に動作することを確認してください。