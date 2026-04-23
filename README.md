KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の骨組みです。  
主な機能は以下の通りです:
- 実運用向け ExecutionEngine（発注／注文管理／リスク管理）
- 監視コンポーネント（システム状態・注文監視・Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量解析、IC 計算）
- AI 支援モジュール（ニュースの NLP によるセンチメント評価、レジーム判定）
- ペーパートレード検証用ツール（レポート生成）

バージョン: 0.1.0

主な機能一覧
-------------
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（本番 / ペーパートレード対応）。
  - run_monitoring.py: SystemMonitor をポーリングして監視を行う。
- 環境設定ツール
  - config_setup.py: .env を対話式に作成/更新するウィザード。
  - validate_config.py: 環境変数や config/*.yaml の検証ツール。
- 監視
  - monitoring/monitoring_engine.py: 各モニタを束ね定期実行。
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py: 個別監視ロジック。
  - monitoring/kill_switch.py: リスクトリガで ExecutionEngine 停止指示（kill.flag）。
  - monitoring/monitoring_db.py: SQLite に監視ログを永続化する層。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算。
  - portfolio/position_sizing.py: 発注量（株数）計算。
  - portfolio/risk_adjustment.py: セクター制限・レジーム乗数。
- リサーチ
  - research/factor_research.py: Momentum/Value/Volatility 等のファクター計算（DuckDB）。
  - research/feature_exploration.py: 将来リターン計算、IC、統計サマリ等。
- AI
  - ai/news_nlp.py: OpenAI を使ったニュースセンチメント集計と ai_scores 書込。
  - ai/regime_detector.py: ETF の MA とマクロニュースを合成して市場レジーム判定。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成。

前提・依存
-----------
推奨 Python バージョン: 3.10+（typing の | 表記等を利用）  
主な Python パッケージ:
- duckdb
- psutil
- openai
- PyYAML（config 検証を有効にする場合）
（sqlite3 は標準ライブラリ、その他標準モジュールを使用）

セットアップ手順
----------------
1. リポジトリをクローン／配置し、仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai PyYAML
   （テストや追加のユーティリティがあれば適宜追加）

3. .env の作成:
   - 対話式で作成: python -m kabusys.config_setup
   - もしくは手動で .env をプロジェクトルートに作成（.env.example を参照）

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（ai モジュール使用時）
   - LOG_LEVEL（デフォルト: INFO）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

4. 設定検証（起動前推奨）:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

5. データディレクトリ等の作成（必要に応じて）:
   - mkdir -p data logs

使い方
------
起動系
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可（デフォルト 60）
  - 監視は本番 sqlite_path を使用（環境に依らず）

- ExecutionEngine 起動（発注エンジン）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込む（本番 DB と完全分離）
  - 実行時、スクリプトはプロセス優先度を上げる（set_process_priority("high")）

停止・Kill Switch
- 外部からプロセスを優雅に停止するにはプロジェクトの data ディレクトリに stop flag を作る：
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します。
- 監視側がリスク条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を指示します。
  - 設定で起動時に kill.flag を自動クリアするか制御できます（KILL_FLAG_CLEAR_ON_START=1 でクリア、デフォルト 0）

ログ
- ロギングは共通ユーティリティで構成されます（kabusys.utils.logging_setup.setup_logging）。
- ログ出力先:
  - stdout（StreamHandler）
  - 日次ローテーションファイル logs/<app_name>.log（TimedRotatingFileHandler、30 日分保持）
- 環境変数 LOG_LEVEL／LOG_DIR で挙動を制御可能

AI 関連
- news_nlp と regime_detector は OpenAI を利用（OPENAI_API_KEY 必須）。
- LLM 呼び出しはレート制限・ネットワーク問題に対して指数バックオフでリトライする実装。
- 失敗時はフォールバック（例: マクロセンチメント=0）するなどフェイルセーフを重視。

ユーティリティ
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

ディレクトリ構成（主なファイル）
--------------------------------
（プロジェクトルート: src/kabusys を想定）

- src/kabusys/
  - __init__.py                         — パッケージ定義（__version__）
  - config.py                           — 環境変数・設定読み込み（.env 自動読み込み含む）
  - config_setup.py                     — .env 作成ウィザード
  - validate_config.py                  — 起動前検証 CLI
  - run_monitoring.py                   — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py      — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                       — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py                — マーケットレジーム判定
  - monitoring/
    - monitoring_db.py                  — SQLite 永続化層（監視ログ）
    - monitoring_engine.py              — 監視エンジン（複数 Monitor の統合）
    - system_monitor.py                 — システム状態 / データ鮮度監視
    - risk_monitor.py                   — ドローダウン / ポジション上限監視
    - kill_switch.py                    — Kill Switch 実装（kill.flag 作成等）
    - trade_monitor.py                  — 注文・約定監視（存在する場合）
    - alert_manager.py                  — アラート通知管理（存在する場合）
  - portfolio/
    - portfolio_builder.py              — 候補選定・重み計算
    - position_sizing.py                — 株数・資金配分計算
    - risk_adjustment.py                 — セクター制限・レジーム調整
  - research/
    - factor_research.py                — ファクター計算（DuckDB）
    - feature_exploration.py            — IC・統計解析など
  - utils/
    - logging_setup.py                  — 統一ロギング設定
    - process_priority.py               — プロセス優先度 / CPU affinity 設定
  - data/                                — 実行時に使用する DB / flag / pid 等（デフォルト）
    - monitoring.db (SQLITE_PATH デフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
    - kabusys.duckdb (DUCKDB_PATH デフォルト)
    - kill.flag / stop_requested.flag / execution.pid (運用時利用)

開発メモ
--------
- DuckDB 接続を受け取り SQL 内で集計処理を行う設計です（リサーチモジュール）。
- AI モジュールは外部 API（OpenAI）の呼び出しを含むため API キー管理に注意してください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch の設定に特に注意してください（validate_config の警告を必ず確認）。

よくある操作例
--------------
- .env を作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 監視を 60 秒間隔で起動:
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring
- Execution をペーパートレードモードで起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- ペーパートレードレポート生成（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（この README にはライセンス情報は含めていません。必要に応じて LICENSE を追加してください。）

お問い合わせ
------------
実運用／導入にあたっては設定や API キーの管理、Kill Switch の運用手順を十分に確認してください。README の補足やサンプル .env を用意すると導入がスムーズです。