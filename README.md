KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤を想定した Python パッケージです。本リポジトリには以下の主要機能群が実装されています。

- ExecutionEngine（発注実行）と監視（Monitoring）の起動スクリプト
- 環境設定ウィザード（.env 生成）と設定検証ツール
- 監視ログ（SQLite）永続化レイヤーと複数の監視コンポーネント（システム / 発注 / リスク）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- リサーチモジュール（ファクター計算、特徴量解析）
- AI 補助モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 各種ユーティリティ（ロギング設定、プロセス優先度設定 等）
- Paper Trading 用の検証レポート生成ツール

主な設計方針:
- 本番 DB と paper_trading 用 DB を分離（KABUSYS_ENV に応じた挙動）
- ルックアヘッドバイアス回避（date.today()/datetime.now() の直接参照回避など）
- フェイルセーフ: 外部 API 失敗時はフォールバックして稼働継続
- 単体関数化（ポートフォリオ / リサーチ等は DB に依存しない純関数群）

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を使い paper_trading.db を利用。
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録。MONITOR_POLL_INTERVAL で間隔指定可（デフォルト 60 秒）。
- 環境設定
  - config_setup.py: 対話式ウィザードで .env を生成／更新
  - validate_config.py: .env および config/*.yaml の存在・基本整合性チェック
- 監視関連
  - monitoring/monitoring_db.py: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py 等
  - Kill Switch: 条件により data/kill.flag を書いて ExecutionEngine を停止させる
- ポートフォリオ
  - portfolio/*.py: 候補選定、重み計算、セクター上限適用、ポジションサイズ計算（lot 単位丸め・aggregate cap 対応）
- リサーチ
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily/raw_financials を参照）
  - research/feature_exploration.py: 将来リターン計算、IC 計算、統計サマリ等
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を集約して LLM で銘柄ごとにセンチメントを算出し ai_scores に書き込む
  - ai/regime_detector.py: ETF とマクロニュースを組み合わせて日次の市場レジーム（bull/neutral/bear）を判定・保存
- ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析して検証レポートを生成
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ラッパー

セットアップ手順
----------------
前提:
- Python 3.10 以上（型注釈で | を使用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証で任意）

推奨セットアップ例（仮想環境内で）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML

   （開発用にパッケージ化されているなら）pip install -e .

3. .env の初期化（対話式）
   - python -m kabusys.config_setup
   - ウィザードに従って JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD などを設定してください
   - .env はセキュリティ上 Git にコミットしないでください

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も終了コード 1 扱いになります

主要な環境変数
----------------
主なキー（config_setup.py 参照）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL（INFO 等）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring 用）

使い方（起動例）
----------------
- .env を準備したら各モジュールを起動します。

ExecutionEngine を起動:
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします
  - 実行中は data/execution.pid に PID を出力する仕様（設定により変更可）

Monitoring を起動:
- MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用する設計です
  - 停止は data/stop_requested.flag の作成で行います（存在検知でループを抜けます）

設定ウィザード:
- python -m kabusys.config_setup

設定検証:
- python -m kabusys.validate_config
- python -m kabusys.validate_config --strict

Paper Trading 検証レポート生成:
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能

AI 機能（ニューススコアリング / レジーム判定）:
- ai.news_nlp.score_news(conn, target_date, api_key=...) を用いる（DuckDB 接続が必要）
- ai.regime_detector.score_regime(conn, target_date, api_key=...) を用いる
- OpenAI API を利用するため OPENAI_API_KEY が必要（引数で上書き可）
- API 呼び出しは冗長性（リトライ・バックオフ）とレスポンス検証を備えています

ログ・監視・停止
----------------
- ログ: utils.logging_setup.setup_logging を各起動スクリプトで呼び出し、stdout と logs/<app_name>.log（デイリーローテート）に出力します
- Kill Switch: monitoring モジュールが条件を満たすと data/kill.flag を書き込み、Execution 側がフラグを検出して安全に停止します
- 停止フラグ: data/stop_requested.flag により run_monitoring/run_execution のポーリング/ループを抜けます

ディレクトリ構成
----------------
以下はパッケージ内の主要ファイル・モジュール構造の要約（src/kabusys 以下）:

- __init__.py
- config.py — 環境変数 / Settings
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — レジーム判定（OpenAI + ETF MA）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各監視コンポーネント
  - monitoring_engine.py — 複数モニタの統合
  - kill_switch.py, alert_manager.py（アラート管理は存在）
- execution/  （発注関連コンポーネント群: BrokerFactory, ExecutionEngine, OrderManager 等）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター制限 / レジーム乗数
- research/
  - factor_research.py — ファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計
- data/（運用時に生成される想定）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB）
  - kill.flag, stop_requested.flag, execution.pid などの制御ファイル
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

注意事項・運用上のヒント
-----------------------
- 環境変数自動読み込み:
  - プロジェクトルートに .env/.env.local があれば自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- 本番 (KABUSYS_ENV=live) では LINE 通知などの設定を必ず確認してください（validate_config が警告を出します）
- OpenAI を用いる機能は API キーに従った料金が発生します。利用前に十分に試験して下さい
- ログディレクトリ作成に失敗した場合はファイルロギングをスキップして stdout のみになります
- Paper Trading は本番 DB とデータ分離されるため検証に利用できます

ライセンス・貢献
----------------
本 README に記載の内容はコードベースから抽出した概要です。実際に運用する際はコード内の docstring や実装をよく確認し、適宜テスト・監査を行ってください。貢献の際は issue / PR を通して変更点を説明してください。

補足（最小 .env 例）
--------------------
以下は最低限必要なキー（サンプル）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

以上。必要なら README をさらに詳細化（コマンド例、systemd ユニット例、テスト手順、API 利用例など）します。どの項目を追加しますか？