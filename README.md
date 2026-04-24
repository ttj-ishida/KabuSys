KabuSys — 日本株自動売買システム（README）
==================================

概要
----
KabuSys は日本株の自動売買 / 監視 / 研究用ユーティリティ群をまとめた Python パッケージです。  
主な目的は以下です。

- 発注エンジン（ExecutionEngine）による自動発注（本番 / ペーパートレード対応）
- システム稼働状況・取引状況の監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算等の純粋関数群（Portfolio）
- ファクター計算・特徴量探索などのリサーチ機能（Research）
- ニュース NLU を用いたセンチメント評価・レジーム判定（AI）
- 運用支援ツール（設定ウィザード・設定検証・検証レポート等）

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / ペーパートレードを切替）
  - run_monitoring.py — SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔指定）
- 設定管理 / ツール
  - config_setup.py — .env を対話式に作成 / 更新するウィザード
  - validate_config.py — .env や config/*.yaml の事前検証 CLI（--strict モードあり）
  - tools/paper_verification_report.py — ペーパートレード DB の検証レポート生成
- 監視関連
  - monitoring_db.py — SQLite を用いた監視ログ永続化（テーブル作成・マイグレーション含む）
  - system_monitor.py / risk_monitor.py / kill_switch.py / monitoring_engine.py — 各種監視ロジック
- ポートフォリオ構築（純粋関数）
  - portfolio_builder.calc_equal_weights / calc_score_weights / select_candidates
  - position_sizing.calc_position_sizes（単元丸め・リスク/上限制御を考慮）
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier
- リサーチ
  - research.factor_research — momentum / volatility / value ファクター計算（DuckDB 経由）
  - research.feature_exploration — 将来リターン計算・IC 等の統計解析
- AI（OpenAI）
  - ai.news_nlp.score_news — ニュース記事を LLM でスコア化して ai_scores テーブルへ書込
  - ai.regime_detector.score_regime — ma200 とマクロ記事の LLM 評価を合成して market_regime を更新
- ユーティリティ
  - utils.logging_setup.setup_logging — stdout + 日次ローテートファイルハンドラの統一設定
  - utils.process_priority.set_process_priority / set_cpu_affinity — プロセス優先度制御

セットアップ手順
----------------
前提
- Python 3.10+（型ヒントに Python 3.10 の構文を使用）
- SQLite（標準ライブラリ）
- DuckDB（分析用 DB）
- psutil（プロセス / リソース監視）
- OpenAI SDK（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を行う場合。任意）

インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

3. ディレクトリ作成（初回）
   - mkdir -p data logs

.env の準備
- 対話式で作る（推奨）
  - python -m kabusys.config_setup
  - ウィザードは .env（デフォルト）を生成します。JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須項目に注意。

設定検証
- python -m kabusys.validate_config
- --strict をつけると警告も失敗扱いになります。

使い方（起動・主要コマンド）
---------------------------
基本的な起動例（ログ・DB・.env を準備済みの前提）

- ExecutionEngine（自動発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db を使用して本番 DB と分離。
    - プロセス優先度を "high" にセット（可能な場合）。
    - _STOP_FLAG（data/stop_requested.flag）があると起動を中止 / 停止する。
    - PID ファイル: data/execution.pid（デフォルト。Settings.pid_file_path 参照）

- Monitoring 起動（単体で SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は production sqlite_path（Settings.sqlite_path）を使用（KABUSYS_ENV に依存しない）。
  - stop フラグ: data/stop_requested.flag（存在でループを抜ける）

- .env の自動読み込み
  - 実行時に自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数が優先）。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うことも可能（デフォルト: data/paper_trading.db）

- AI 機能（プログラム利用）
  - OpenAI API キー: 環境変数 OPENAI_API_KEY を設定
  - 例（スクリプトで呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)

主要設定（環境変数）
------------------
- 必須（運用に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: Execution は data/paper_trading.db を使用
    - live: 本番（注意・警告あり）

- DB / ログ
  - DUCKDB_PATH: data/kabusys.duckdb（DuckDB 分析 DB）
  - SQLITE_PATH: data/monitoring.db（監視用 SQLite）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
  - logs/<app_name>.log に日次ローテートで出力（30 日保持）

- AI（OpenAI）
  - OPENAI_API_KEY: OpenAI 呼び出しに必要

- 監視 / 制御
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH: data/kill.flag（KillSwitch のパス。Settings.kill_flag_path）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production での 1 は危険）

- Paper Trading（挙動）
  - PAPER_FILL_MODE: instant | partial | never | reject（MockBrokerClient の約定挙動）

停止フラグ / Kill Switch
-----------------------
- 停止リクエスト（外部からループ停止）
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止用フラグファイル
- Kill Switch（運用自動停止）
  - KillSwitch により data/kill.flag が書き込まれると ExecutionEngine 停止などのトリガーに使われる。
  - validate_config では本番環境で KILL_FLAG_CLEAR_ON_START=1 を使う場合に警告を出します。

内部 API の利用（簡単な説明）
----------------------------
- Portfolio（純粋関数）
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates) / calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, allocation_method=...)
- Research（DuckDB 接続を渡す）
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
- AI
  - score_news(duckdb_conn, target_date, api_key=None)
  - score_regime(duckdb_conn, target_date, api_key=None)

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                  — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
- src/kabusys/utils/
  - logging_setup.py           — 共通ログ設定（stdout + 日次ローテート）
  - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ
- src/kabusys/monitoring/
  - monitoring_db.py           — monitoring DB スキーマ / 持続化 API
  - system_monitor.py          — システム状態・データ鮮度監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag 管理
  - monitoring_engine.py       — 各 Monitor を束ねるループ
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py                — ニュースの LLM センチメント評価
  - regime_detector.py         — レジーム判定（ma200 + LLM）
- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

運用上の注意
--------------
- 本番環境（KABUSYS_ENV=live）では設定値・アクセストークンの管理に十分注意してください。
- .env は絶対に Git にコミットしないでください（config_setup.py にも注意書きあり）。
- run_execution / run_monitoring は stop flag（data/stop_requested.flag）を参照します。手動停止や CI での制御はこのフラグを使うことができます。
- AI 機能は OpenAI API へ課金が発生します。呼び出し頻度・バッチサイズに注意してください。
- validate_config.py で設定検証を行い、--strict オプションでより厳密なチェックを適用できます。

トラブルシューティング
---------------------
- ログファイルが出力されない / ログディレクトリ作成失敗
  - LOG_DIR 環境変数の設定やパーミッションを確認。logging_setup は作成失敗時にコンソールのみで継続します。
- DuckDB / SQLite が見つからない・接続エラー
  - DUCKDB_PATH / SQLITE_PATH のパスを確認し、ディレクトリが存在するか検証してください（validate_config 参照）。
- OpenAI 呼び出しが失敗する
  - OPENAI_API_KEY を正しく設定、ネットワーク接続、API のレート制限に注意。news_nlp/regime_detector にはリトライロジックが実装されていますが、キー未設定は例外になります。

開発者向けメモ
----------------
- Settings クラスはプロパティを通じて環境変数を解決します。単体テスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- monitoring_db.init_monitoring_db は既存 DB に対するマイグレーション（カラム追加）を持ちます。
- research モジュールは DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照します。外部 API 呼び出しは行いません（テスト容易性のため）。

付録: よく使うコマンド例
-----------------------
- .env を作る（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

お問い合わせ / 貢献
-------------------
- 仕様変更・不具合修正はソースコードを参照し、Pull Request を送ってください。README の改善提案も歓迎します。

以上。必要に応じて README に追記（依存関係厳密版、設定例テンプレート、運用フロー図など）できます。どの情報を追加したいか指示してください。