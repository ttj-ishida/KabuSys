README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能群が含まれます。

- ExecutionEngine（発注エンジン）起動スクリプト
- Monitoring（システム監視 / リスク判定 / Kill Switch）
- Portfolio construction（銘柄選定・配分・株数決定）
- Research / factor 計算（DuckDB を用いたファクター計算）
- AI モジュール（ニュースの LLM スコアリング / レジーム判定）
- 開発用ユーティリティ（.env ウィザード・設定検証・ペーパートレード検証レポート）

主な特徴
--------
- 環境変数/.env による構成管理（自動読み込み機能あり）
- Execution と Monitoring の分離（Monitoring は本番の監視 DB を参照）
- KABUSYS_ENV によるモード切替（development / paper_trading / live）
- Paper Trading 用に本番 DB と完全分離された専用 SQLite を使用可能
- DuckDB を使ったオンデマンド分析・ファクター計算
- OpenAI を使ったニュースセンチメント評価（オプション）
- kill.flag / stop_requested.flag を用いたシンプルな停止制御

セットアップ手順
----------------

1. リポジトリを取得
   - git clone ... を実行して取得してください。

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (config/*.yaml の検証を使う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使ってください。なければ上記を参考にインストールします）

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で作成。
   - 自動ロード: プロジェクトルートに .env / .env.local があれば、起動時に自動で読み込まれます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を fail にしたい場合は --strict を付ける

6. データディレクトリの準備
   - デフォルトでは data/ 以下に DB 等を作成します。必要なディレクトリが自動作成されますが、パーミッションに注意してください。

主要な環境変数（抜粋）
----------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 運用 / 任意:
  - KABUSYS_ENV           : execution モード（development / paper_trading / live） デフォルト: development
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite（monitoring.db）デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY        : OpenAI API キー（AI モジュール利用時）
  - PAPER_FILL_MODE       : paper_trading 時の約定モード ("instant" | "partial" | "never" | "reject") デフォルト "instant"
  - MONITOR_POLL_INTERVAL : Monitoring のポーリング間隔（秒、デフォルト 60）

デフォルト値（主なもの）
-----------------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- Monitoring ポーリング間隔: 60 秒

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（注文エンジン）起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と完全分離）。
    - エンジンは data/execution.pid に PID を書きます。
    - 停止は data/stop_requested.flag を作成することで受け付けます（または Kill Switch による data/kill.flag）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 備考:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視は常に本番 DB を見る設計）。

- Paper Trading 検証レポート（標準出力）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用できます。

- AI / リサーチ API（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースの LLM スコアを ai_scores テーブルに書き込みます（OpenAI API キー必須）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定を行い market_regime テーブルへ書き込みます。
  - リサーチ関数（例）:
    - kabusys.research.calc_momentum(duckdb_conn, target_date)
    - kabusys.research.calc_volatility(...)
    - kabusys.research.calc_value(...)

停止と Kill / Stop フラグ
-------------------------
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループはこのファイルを検知すると安全にシャットダウンします。
- data/kill.flag
  - KillSwitch により ExecutionEngine 停止を要求する用途に使用されます。Settings.kill_flag_clear_on_start を 1 にすると起動時に自動クリアしますが、本番では 0 を推奨します。
- data/execution.pid
  - Execution エンジンの PID を書きます。SystemMonitor は PID ファイルの stale（既に存在するがプロセスがいない）検出・削除を行います。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を想定）

- __init__.py
  - パッケージのバージョン等

- config.py
  - .env 自動ロード、Settings クラス（環境変数アクセスラッパー）

- config_setup.py
  - .env 対話式ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper/live 切替）

- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト

- monitoring/
  - monitoring_db.py      : 監視用 SQLite 永続化層（テーブル作成・CRUD ユーティリティ）
  - system_monitor.py     : CPU/メモリ/ディスク・データ鮮度・プロセス検査
  - trade_monitor.py      : 注文滞留・約定異常価格チェック
  - risk_monitor.py       : ドローダウン・ポジション上限監視、ダッシュボード更新
  - kill_switch.py        : Kill Switch（kill.flag 書き込みロジック）
  - monitoring_engine.py  : 各モニタを束ねるランナー
  - alert_manager.py      : （アラート送信の抽象 / 実装は実装箇所を参照）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...（発注ロジック群）
  - order_record.py など（注文状態を表すクラス群）

- portfolio/
  - portfolio_builder.py  : 候補選定・重み計算
  - position_sizing.py    : 株数決定（lot 単位丸め・集計 cap）
  - risk_adjustment.py    : セクター上限・レジーム乗数

- research/
  - factor_research.py    : momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリなど

- ai/
  - news_nlp.py           : ニュース記事を LLM で採点して ai_scores に書き込む
  - regime_detector.py    : ETF MA と LLM を組み合わせた市場レジーム判定

- tools/
  - paper_verification_report.py : Paper Trading の検証レポート出力

- utils/
  - process_priority.py   : psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ

設計上の注意・運用メモ
---------------------
- Monitoring は常に本番の監視 DB（SQLITE_PATH）を参照する設計です。設定ミスで監視対象を誤ることがないよう注意してください。
- Paper Trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録されるため、本番 DB とは分離されています。ペーパートレードを行う際は KABUSYS_ENV=paper_trading を必ず設定してください。
- OpenAI API を使う機能は外部 API 呼出しとネットワーク依存があるため、API キーの管理とレート制限・再試行ロジックの理解を推奨します（実装内でエクスポネンシャルバックオフを行います）。
- process priority / cpu affinity の設定は psutil の権限に依存します。権限不足時は警告を出してスキップします。
- .env は機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。

開発者向け情報
---------------
- DuckDB をデータソースとして前処理・ファクター計算を行うため、prices_daily / raw_financials / raw_news 等のテーブルスキーマに依存します。実行前にテーブルの準備が必要です。
- テストや CI では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化できます。
- 各モジュールは可能な限り副作用を避け、外部依存（API 呼び出し等）は引数で注入または明示的に分離する設計を意識しています（テスト容易性向上）。

サンプル起動例
--------------
1) .env を作成:
   python -m kabusys.config_setup

2) 設定チェック:
   python -m kabusys.validate_config

3) DuckDB / SQLite の準備（データ投入は別スクリプトまたは手動で）.

4) Monitoring の起動:
   MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5) Execution の起動（開発・テスト）:
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution

6) Paper 検証レポート生成:
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

質問・貢献
----------
バグ報告や機能追加の提案は Issue を立ててください。プルリクエスト歓迎します。README に未記載の挙動や追加の実行例が必要であればお知らせください。