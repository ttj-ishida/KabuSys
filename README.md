# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買／調査プラットフォームのコアモジュール群です。  
主に以下を提供します。

- 発注エンジン (ExecutionEngine)
- 監視（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB を用いたオフライン解析）
- ニュースを使った AI（OpenAI）によるセンチメント評価・レジーム判定
- 環境設定ウィザード / 設定検証 CLI / 検証レポート生成ツール

特徴
---
- 明確に分離された「本番 / ペーパートレード」DB（paper_trading 実行時は専用 SQLite を使用）
- DuckDB を用いた高速なバッチ解析（prices_daily / raw_financials 等）
- リスク管理（ドローダウン、ポジション上限）と自動停止（Kill Switch）
- OpenAI を利用したニュースセンチメント（AIスコア）・レジーム判定（オプション）
- ログは標準出力＋日次ローテートファイルに出力（logs/）
- .env ウィザードと起動前の設定検証ツールを提供

前提依存ライブラリ（代表）
---
（プロジェクトに requirements.txt がない場合は下記をインストールしてください）
- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証に必要）
- その他標準ライブラリ

セットアップ手順
---
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt があれば pip install -r requirements.txt）

4. 初期設定ファイルの作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに .env が作成されます（.env は絶対にコミットしないでください）

5. 設定の事前チェック（起動前）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります

6. データディレクトリ
   - デフォルトの DB / ログ保存先:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じて .env でパスを変更してください（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）

主要な環境変数（主要なもののみ）
---
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO、DEBUG）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔、秒; デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番で自動クリアするか。0 推奨）

主要な実行方法 / 使い方
---
- ExecutionEngine（売買エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - 起動中に data/stop_requested.flag を作成するとエンジンは停止します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60 秒）
  - 監視は Settings にかかわらず production の sqlite_path を使用して監視 DB を扱います
  - data/stop_requested.flag を作成するとループを終了します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH の上書き）

ライブラリ API（代表）
---
- kabusys.config.Settings / settings — 環境変数ラッパ
- kabusys.portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights（候補選定／重み）
  - calc_position_sizes（株数決定）
  - apply_sector_cap, calc_regime_multiplier（リスク調整）
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary（特徴量解析）
- kabusys.ai:
  - score_news(conn, target_date, api_key=None) — ニュースセンチメントを ai_scores に書込
  - score_regime(conn, target_date, api_key=None) — レジーム判定を書込

監視・リスク関連の挙動
---
- MonitoringDB（monitoring/monitoring_db.py）:
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理（初期化・マイグレーションあり）
- KillSwitch（monitoring/kill_switch.py）:
  - RiskMonitor / SystemMonitor / TradeMonitor の結果を評価して data/kill.flag を書き込み ExecutionEngine 停止を指示
- RiskMonitor:
  - ドローダウン、ポジション上限の判定と dashboard/risk_logs への記録

注意事項 / 運用メモ
---
- .env はデフォルトで自動読み込みされます（プロジェクトルートが検出できる場合）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時は KABUSYS_ENV=live を設定し、LINE のトークンを設定しておくことでアラート通知が可能です（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）。
- MONITORING は監視 DB を使用します。monitoring は Settings.env に依存せず sqlite_path（監視用 DB）を参照します（監視ログは本番 DB を参照するよう設計）。
- OpenAI API を使う機能（ai.news_nlp, ai.regime_detector）は API キーとネットワークアクセスが必要です。失敗時はフェイルセーフでデフォルト値にフォールバックする設計ですが、キーは必須です。
- process priority / CPU affinity は utils/process_priority.py で設定され、起動スクリプトは優先度 "high" を設定します。権限不足等で失敗することがあります（警告ログが出ます）。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソール出力のみになります。

ディレクトリ構成（主要ファイル）
---
（src/kabusys をルートとした概観）

- kabusys/
  - __init__.py
  - run_execution.py                — ExecutionEngine の起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - config.py                       — Settings（環境変数読み込み・検証）
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成ツール
  - ai/
    - news_nlp.py                    — ニュースの LLM センチメント評価
    - regime_detector.py             — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py               — monitoring DB 用の永続化層
    - monitoring_engine.py           — 各 Monitor の束ね（ポーリング実行）
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — （取引関連監視）※実装ファイル参照
    - risk_monitor.py                — ドローダウン・ポジション制限監視
    - kill_switch.py                 — Kill Switch（flagファイル操作）
    - alert_manager.py               — （アラート送信ロジック）※実装ファイル参照
  - execution/
    - execution_engine.py            — ExecutionEngine 本体（セッション実行）
    - order_manager.py               — 注文管理
    - order_repository.py            — 注文履歴永続化
    - broker_factory.py              — BrokerClient の生成（本番/モック選択）
    - reconciler.py, risk_manager.py — 実行補助コンポーネント
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み算出
    - position_sizing.py             — 株数計算・キャップ処理
    - risk_adjustment.py             — セクター制限・レジーム乗数
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py               — 統一ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity 設定
  - data/                            — デフォルトで DB / フラグ / PID を置く（config で上書き可）
  - config/                          — YAML 設定ファイル群（system_config.yaml 等）

さらに読むべきファイル
---
- 各モジュール先頭の docstring に設計方針・振る舞いが詳述されています。実装や運用の調整はそちらを参照してください。

問題が発生したら
---
- validate_config で設定の問題を検出できます。
- ログ（logs/<app>.log）を確認してください。
- 質問やバグ報告はリポジトリの issue に記載してください。

ライセンス / バージョン
---
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

以上。運用上の微調整や拡張（例: 銘柄ごとの lot_size、手数料モデルの導入、AI モデルの切替など）は各モジュールに注記がありますので参照して実装してください。