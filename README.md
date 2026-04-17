README
=====

概要
----
KabuSys は日本株の自動売買支援ライブラリ／アプリケーション群です。  
戦略（ファクター計算・特徴量解析）・ポートフォリオ構築・ポジションサイズ計算・発注実行（本番 / ペーパートレード）・監視（システム、注文、リスク）・AI（ニュース NLP / レジーム判定）・各種ユーティリティを含みます。

主な設計方針
- DuckDB / SQLite をデータ基盤に利用し、分析用テーブルと監視ログを分離
- Paper trading は本番 DB と完全に分離（別 SQLite ファイル）
- AI（OpenAI）呼び出しはフェイルセーフ設計（リトライ・フォールバック）
- .env による環境変数管理、対話式ウィザード・検証ツールを提供
- モジュール群はライブラリとしても利用可能（research / portfolio / ai など）

機能一覧
--------
- 環境設定
  - 対話式 .env ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い data/paper_trading.db に記録
    - PID ファイル管理、停止フラグ対応
- 監視プロセス
  - python -m kabusys.run_monitoring
    - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）
    - 監視ログは SQLite（settings.sqlite_path）へ永続化
- モデル・研究
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリ
- ポートフォリオ構築
  - 候補選定、等ウェイト / スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- AI
  - ニュース NLP による銘柄センチメント評価（OpenAI）
  - マクロニュース + ma200 を合成した市場レジーム判定（OpenAI）
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - 監視 DB の永続化レイヤ（monitoring_db）

前提・依存
-----------
- Python 3.10+
  - typing の | 演算子などを使用
- 推奨パッケージ（最低限）
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（config YAML の内容検証に任意で使用）
- SQLite（Python 標準ライブラリに同梱）
- ネットワーク（OpenAI / LINE API を利用する場合）

セットアップ手順
----------------
1. リポジトリをチェックアウト
   - プロジェクトルートに src/ 配下のパッケージ一式が存在します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を生成：
     - python -m kabusys.config_setup
   - 生成された .env を編集して必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。
   - 自動ロードが望ましくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

6. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定するか、各関数に api_key を渡してください。

使用方法
--------
基本的なコマンド例
- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に従う
    - development: 実注文を送らない開発モード
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB とは分離）
    - live: 実際に発注を行う本番モード（注意して使用）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作るとループが終了します

- Paper Trading 検証レポート（任意期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合: --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- OPENAI_API_KEY (AI 機能で必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒数。run_monitoring で参照）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険。0 推奨）

停止・Kill Switch
- 監視側は条件を満たすと data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（KillSwitch）。
- 実行中のエンジン停止（外部から）にはプロジェクトルート/data/stop_requested.flag を作成します（run_execution/run_monitoring は存在を確認して終了します）。
- PID ファイル: data/execution.pid （run_execution が起動中に書き込む）

ライブラリ API（主要）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats 経由）
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier
- kabusys.ai
  - score_news(conn, target_date, api_key=None) — ニュース NLP を使った銘柄スコア（DuckDB 接続）
  - score_regime(conn, target_date, api_key=None) — レジーム判定（ai.regime_detector）

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数読み込み・Settings
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリングスクリプト

サブパッケージ（代表）
- ai/
  - news_nlp.py                  — ニュース NLP（OpenAI）
  - regime_detector.py           — 市場レジーム判定（OpenAI）
- monitoring/
  - monitoring_db.py             — SQLite 監視 DB 層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
- execution/                     — 発注関連（エンジン / order_manager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

（ファイル一覧はこの README の作成時点での代表的なものを抜粋しています）

運用上の注意
------------
- 本番（KABUSYS_ENV=live）での実行は細心の注意を払い、まずは paper_trading / development で動作確認を行ってください。
- KILL_FLAG_CLEAR_ON_START=1 は本番環境で危険です（自動で kill.flag をクリアしてしまうため）。デフォルト 0 を推奨。
- OPENAI_API_KEY を用いる機能は API コストとレイテンシが発生します。トークン管理・レート制限に注意してください。
- process_priority 設定は OS 権限に依存し、失敗することがあります（警告ログのみ）。psutil の権限要件に注意。

トラブルシューティング（簡易）
------------------------------
- .env が自動ロードされない場合:
  - プロジェクトルートが自動検出されない可能性があります（.git または pyproject.toml を基準に検出）。その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を用意してください。
- 依存ライブラリ未インストール:
  - validate_config で PyYAML 未インストールを警告します。必要に応じて pip install PyYAML。
- OpenAI 呼び出し失敗:
  - ネットワーク、APIキー、レート制限、レスポンスパースエラーなどの可能性があります。ログを確認し適宜リトライ設定を調整してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期リリース）

最後に
------
この README はコードベース内のモジュール解説・起動手順のサマリです。詳細な設定や挙動（各種パラメータ、PoV・アルゴリズム設計の背景など）はソース内の docstring やコメントを参照してください。質問や特定の機能に関するドキュメント化が必要であれば、対象モジュールを指定して詳しい README / チュートリアルを作成します。