KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ / 実行スクリプト群です。  
本リポジトリには以下の主要機能群が含まれており、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・資金配分、リサーチ（ファクター計算）、AI（ニュースのセンチメント評価・市場レジーム判定）、ユーティリティ／ツール類が実装されています。

バージョン: 0.1.0

特徴（主な機能）
----------------
- Execution
  - ExecutionEngine（発注実行）と関連コンポーネント（OrderManager, OrderRepository, Reconciler, RiskManager 等）
  - paper_trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と完全分離
- Monitoring
  - SystemMonitor（CPU・メモリ・ディスク・プロセス生存確認・データ鮮度）
  - TradeMonitor / RiskMonitor（滞留注文やドローダウン・ポジション上限の監視）
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - 永続化: SQLite 監視 DB（monitoring_db.py）
  - Monitoring のポーリングループ起動スクリプト（run_monitoring）
- Portfolio（銘柄選定・重み計算・ポジションサイジング）
  - 等金額 / スコア加重 / リスクベースの発注株数計算
  - セクター集中制限、レジーム乗数（regime に応じた投下資金スケール）
- Research
  - DuckDB を用いたファクター計算（Momentum, Volatility, Value など）
  - 将来リターン計算、IC（情報係数）、統計サマリ等
- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントのバッチ評価と ai_scores テーブルへの書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントの合成による市場レジーム判定
  - OpenAI API のリトライ / バックオフ・レスポンス検証ロジックを実装
- ユーティリティ
  - 設定ウィザード（config_setup）で .env の対話的生成
  - 設定検証 CLI（validate_config）
  - ロギング設定ユーティリティ（logging_setup）: stdout + 日次ローテーションファイル
  - プロセス優先度・CPU affinity 設定ユーティリティ（process_priority）
- ツール
  - paper_verification_report: ペーパートレード結果（稼働率・成功率・レイテンシ等）のレポート生成

前提（依存関係）
----------------
- Python 3.10 以上（型アノテーション表記に依存）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（機能によって必要）
  - PyYAML（config/*.yaml の内容検証に使用。validate_config の一部で任意）
- SQLite は標準ライブラリで利用

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - YAML 検証を行いたい場合は pip install pyyaml

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードに従って J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを入力します
   - もしくは手動で .env を作成（.env.example を参考に）

5. 設定の検証
   - python -m kabusys.validate_config
   - 本番環境では --strict を付けて警告も失敗とする: python -m kabusys.validate_config --strict

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db を使う
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方（起動・実行例）
--------------------
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に記録
  - 実行中は data/execution.pid に PID を書き込み、data/stop_requested.flag や data/kill.flag による停止を検知します

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は Settings に従って本番 sqlite_path を使います（Monitoring は環境にかかわらず本番 sqlite を参照する設計）

- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗 (exit code 1) と扱う

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプションで SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラムからの呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続（duckdb.connect(...) の返り値）
    - target_date: 日付オブジェクト
    - api_key: None の場合は環境変数 OPENAI_API_KEY を使用
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に OpenAI キーを渡して実行

- Kill Switch / 手動停止
  - KillSwitch はドローダウンやポジション上限等の条件で data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る設計
  - kill.flag の位置は Settings.kill_flag_path（デフォルト data/kill.flag）
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアする（本番では 0 推奨）

ロギング
--------
- 共通の logging 設定: kabusys.utils.logging_setup.setup_logging(app_name="...") を各スクリプトが呼び出します
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/<app_name>.log）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御

ディレクトリ構成（主要ファイル）
-----------------------------
（リポジトリの src/kabusys 以下を抜粋した概観）

- src/kabusys/
  - __init__.py
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - config.py                 — 環境変数 / 設定読み込みロジック（Settings）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視ログ永続化
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - （※ trade_monitor 等の監視ロジックも存在）
  - portfolio/
    - portfolio_builder.py    — 候補選定 / ウェイト計算
    - position_sizing.py      — 発注株数計算（リスクベース等）
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — モメンタム・バリュー・ボラティリティ等の計算（DuckDB 使用）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携・バッチ処理）
    - regime_detector.py      — レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

運用上の注意
------------
- 本番（KABUSYS_ENV=live）での起動前には必ず python -m kabusys.validate_config を実行し、設定を確認してください。
- OpenAI API を使う機能は外部 API 呼び出しのため、API キーの管理やコストに注意してください。
- paper_trading モードは本番 DB と完全に分離されますが、設定ミスに注意してください（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH の確認）。
- モニタリングはデフォルトで本番 sqlite_path を参照します（監視 DB は環境に関係なく本番 DB を使用する設計）。

開発者向けメモ
--------------
- .env の自動読み込みはデフォルトで有効（config.py）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB を使う箇所は conn に DuckDB 接続を渡して使用します（read-only 想定のクエリが多い）。
- テスト時には OpenAI 呼び出し関数をパッチして外部依存を切り離せます（モジュール内で _call_openai_api を差し替え可能）。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

お問い合わせ
------------
実行やセットアップで問題があれば、使用している環境情報（Python バージョン、インストールパッケージ、.env の重要な設定（機密情報は除く））を添えてお問い合わせください。

以上。必要に応じて README に含めるサンプル .env、systemd / supervisor 用の起動ユニット例、より詳細な運用手順（データベース移行、バックアップ、ログローテーション監視など）を追加できます。どの情報を追加したいか教えてください。