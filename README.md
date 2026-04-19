KabuSys
=======

日本株自動売買システムの一部（モジュール群）をまとめたリポジトリです。  
この README は、提供されているスクリプト / モジュール群の概要、セットアップ、基本的な使い方、ディレクトリ構成を簡潔にまとめたものです。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買・研究基盤を想定したコード群です。主要機能は以下を含みます。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じた発注処理、リスク管理、オーダー管理
- Monitoring（監視）: システム状態・データ鮮度・注文ログ・リスク指標のポーリングと永続化、Kill Switch による安全停止
- Portfolio Construction: 候補選定、重み計算、株数決定（リスクベース／等分等）
- Research: ファクター計算（モメンタム / ボラティリティ / バリュー）、特徴量解析（IC 等）
- AI / NLP: ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存、マクロニュースと ETF MA でレジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、環境ファイルウィザード、設定検証、レポートツール 等

主な特徴
--------
- 環境変数 / .env ベースの設定管理（config_setup.py で対話式生成）
- production / paper_trading を分離した DB 設計（paper_trading モードは別 DB を使用）
- DuckDB を用いた分析向けデータ処理（prices_daily / raw_financials 等を想定）
- OpenAI を使ったニュースセンチメント（gpt-4o-mini を想定）およびレジーム判定
- 監視用 SQLite DB（system_status, trade_logs, positions, risk_logs, dashboard）
- Kill Switch（data/kill.flag）による安全停止、stop フラグ（data/stop_requested.flag）によるループ停止
- ログ: stdout 出力 + 日次ローテートファイル（logs/<app>.log）

セットアップ手順
----------------
以下は一般的なセットアップ手順の例です。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要ライブラリをインストール
   - ここでは主要な依存を例示します（requirements.txt がある場合はそちらを使用してください）。
     - pip install duckdb psutil openai
     - PyYAML は設定検証で任意: pip install PyYAML
   - sqlite3 は標準ライブラリに含まれます。

4. .env を作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 主要なデフォルト値（.env 未設定時の挙動）:
     - DUCKDB_PATH = data/kabusys.duckdb
     - SQLITE_PATH = data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
     - KABUSYS_ENV = development（有効値: development / paper_trading / live）
     - LOG_LEVEL = INFO

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. ディレクトリ作成（必要なら）
   - data/ と logs/ は自動作成を試みますが、権限等で失敗することがあるため手動で用意しておくと安全です。

使い方（主要スクリプト）
-----------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成 / 更新します。

- 設定検証
  - python -m kabusys.validate_config
  - .env と config/*.yaml（存在する場合）を検証します。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは data/paper_trading.db に記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に data/stop_requested.flag が作成されるとエンジンは安全に停止を試みます。
    - 実行中の PID は data/execution.pid に書き込まれます（設定により変更可）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使用します（環境に関わらず）。
    - 停止は data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH で SQLite DB を指定。環境変数 PAPER_TRADING_SQLITE_PATH を使うことも可能。

- AI / レジーム関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...).cursor/connection）を受け取り、結果を DB に書き込みます。
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY で提供してください。

設定・環境変数（主なもの）
------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI 関連:
  - OPENAI_API_KEY（AI 機能を使用する場合）
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB パス:
  - DUCKDB_PATH  (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH  (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
- ログ:
  - LOG_LEVEL（DEBUG/INFO/…）
  - LOG_DIR（デフォルト logs/）
- その他:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
  - PAPER_FILL_MODE（paper_trading の MockBroker 動作: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（本番で Kill Switch の自動クリアを行うか。0 が推奨）

停止 / Kill Switch
-----------------
- data/stop_requested.flag
  - run_monitoring / run_execution のループを優雅に終了させるためのフラグファイル。
  - 存在を検知すると各プロセスは終了手続きを行います。

- Kill Switch（自動停止）
  - kabusys.monitoring.KillSwitch はリスク条件（ドローダウン、ポジション上限等）を評価し、
    条件を満たすと data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアします（本番では推奨されません）。

ログ
----
- ログは stdout（コンソール）へ出力され、加えて logs/<app_name>.log に日次ローテートで保存されます。
- setup_logging でログディレクトリの作成を試みますが、作成失敗時はファイル出力が無効化されコンソールのみになります。

ディレクトリ構成（抜粋）
----------------------
以下は主要ファイル/モジュールの概観（src/kabusys 以下）。実際のツリーはローカルリポジトリを参照してください。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数/.env ロード・Settings
  - config_setup.py                -- .env 対話式ウィザード
  - validate_config.py             -- 起動前設定検証ツール
  - run_execution.py               -- ExecutionEngine 起動スクリプト
  - run_monitoring.py              -- SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  -- Paper Trading 検証レポート
  - utils/
    - logging_setup.py             -- ログ設定ユーティリティ
    - process_priority.py          -- プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             -- SQLite 永続化層
    - system_monitor.py            -- システム・データ鮮度監視
    - risk_monitor.py              -- ドローダウン / ポジション監視
    - trade_monitor.py             -- （注文関連の監視: ファイルに含まれる想定）
    - kill_switch.py               -- kill.flag 書き込みユーティリティ
    - monitoring_engine.py         -- 各 monitor を束ねるエンジン
    - alert_manager.py             -- （LINE など通知送信機構: ファイルに含まれる想定）
  - execution/                      -- Execution 系コンポーネント（engine, broker_factory 等）
  - portfolio/
    - portfolio_builder.py         -- 候補選定・重み
    - position_sizing.py           -- 株数決定・スケールダウン
    - risk_adjustment.py           -- セクター上限・レジーム乗数
  - research/
    - factor_research.py           -- momentum/volatility/value の計算
    - feature_exploration.py       -- forward returns / IC / summary
  - ai/
    - news_nlp.py                  -- ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           -- レジーム判定（ETF MA + マクロ NLP）
  - data/                           -- 実行時 DB・flag 等の既定配置（data/monitoring.db 等）

注意事項 / トラブルシューティング
--------------------------------
- .env は機密情報を含むため Git にコミットしないでください（config_setup.py のヘッダにも警告があります）。
- OpenAI API を使う機能は API コストが発生します。テストは少量で行ってください。
- psutil を使った優先度設定は権限により失敗する場合があります（警告ログが出ますが処理は継続します）。
- DuckDB のバージョン差異により executemany に空リストを渡すとエラーになるケースがあるため、該当箇所は空チェック済みです。
- PyYAML がない場合、validate_config の YAML 検証はスキップされます（警告）。

開発者向けメモ
---------------
- 多くのモジュールは「外部副作用を持たない純粋関数」設計（portfolio / research 等）と、DB 書き込みのみを行う永続化層（monitoring_db）に分離されています。
- テスト時は OpenAI 呼び出し関数をモック（unittest.mock.patch）することを想定した実装になっています。

以上がこのコードベースの概要と基本的な利用手順です。具体的な拡張や運用手順（デプロイ、systemd / Supervisor 設定、監視ダッシュボードなど）は環境に応じて追記してください。必要であれば README にサンプル .env のテンプレートや systemd ユニットの例も追加できます。希望があればその形式で追記します。