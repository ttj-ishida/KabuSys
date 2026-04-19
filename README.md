KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買システムの構成要素群です。  
このリポジトリには、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築／ポジションサイズ計算、研究用ファクター計算、ニュース NLP を使った AI スコアリングなどのモジュールが含まれます。  
設計方針としては「環境変数ベースの設定」「SQLite / DuckDB によるローカル永続化」「Paper Trading と Live の切り替え」「フェイルセーフ（部分失敗を許容）」などがとられています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番またはペーパートレード用のブローカークライアントを切替
  - paper_trading では data/paper_trading.db に記録し、本番 DB と分離
  - 実行中は PID ファイル（data/execution.pid）を保持、stop フラグで安全停止
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム稼働状況、データ鮮度、オーダー/約定の監視
  - リスクモニタ（ドローダウン、ポジション上限）による Kill Switch（data/kill.flag）発動
  - アラート発行（AlertManager 経由）
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等配分・スコア重み配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元丸め、集約上限調整）
- 研究用モジュール（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB を利用して価格データを SQL で処理
- AI モジュール（ai パッケージ）
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む
  - 市場レジーム判定（ma200 とマクロニュースの合成）
  - OpenAI API 呼び出しは堅牢なリトライ／検証ロジックを持つ
- ユーティリティ
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - (例) git clone ... && cd <repo>

2. 依存パッケージをインストール
   - 推奨: 仮想環境を作成してからインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
     - pip install -r requirements.txt
   - 主要な依存（必須／推奨）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml の内容検証に使用、なくても動作）

   > requirements.txt がない場合は必要に応じて上記パッケージをインストールしてください。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作成する場合、最低限設定が必要なキー:
     - JQUANTS_REFRESH_TOKEN=<your token>
     - KABU_API_PASSWORD=<your password>
   - 便利なオプション（デフォルト値あり）:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=<your openai key>  (AI 機能を使う場合)

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit(1)

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは logs/ および data/ を使用します。起動時に自動作成されることが多いですが、権限や配置を予め確認してください。

基本的な使い方
-------------
- ExecutionEngine を起動（本番 / ペーパートレード）
  - デフォルト（KABUSYS_ENV に従う）:
    - python -m kabusys.run_execution
  - 明示的にペーパートレードで起動:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行の特徴:
    - プロセス優先度を high に設定しようとします（psutil が必要、権限がない場合は警告）。
    - paper_trading の場合は settings.paper_sqlite_path を使い、本番データと完全分離します。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - 停止は監視プロセスが書き込む kill.flag による、あるいは stop_requested.flag を作成してもらう等の仕組みがあります。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 定期ポーリングで SystemMonitor, TradeMonitor, RiskMonitor を呼び出します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（例: export MONITOR_POLL_INTERVAL=30）。不正値や 0/負数はデフォルト 60 秒にフォールバック。
    - 監視は本番の sqlite_path を使用（KABUSYS_ENV の値に依存しない）。
    - 停止: data/stop_requested.flag が検出されるとループを抜けて終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

- AI 機能（ニューススコア / レジーム判定）
  - モジュール関数を通じて利用します（CLI は用意されていません）。
  - OpenAI API を使うためには OPENAI_API_KEY を設定してください。
  - AI 呼び出しは堅牢にリトライ・検証が組まれていますが API キー・レート制限に注意してください。

ログとファイル
---------------
- ログ:
  - デフォルト出力先: stdout と logs/<app_name>.log（日次ローテーション、30 日保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。
  - LOG_DIR 環境変数でログ保存先を変更可能。

- データベース:
  - DuckDB: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLite（監視）: SQLITE_PATH（デフォルト data/monitoring.db）
  - Paper Trading SQLite: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

- PID / フラグファイル:
  - 実行エンジン PID: data/execution.pid（Settings.pid_file_path）
  - Kill Switch: data/kill.flag（Settings.kill_flag_path）
  - グローバル停止フラグ（run_* が参照）: data/stop_requested.flag
  - kill.flag は KillSwitch が条件を満たした際に書き込む。起動時に自動でクリアする挙動は KILL_FLAG_CLEAR_ON_START による。

環境変数一覧（主なもの）
-----------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 選択・説明:
  - KABUSYS_ENV: development | paper_trading | live （default: development）
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
  - LOG_LEVEL: DEBUG|INFO|...（default: INFO）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=有効、0=無効、default: 0）

停止とフェイルセーフ
-------------------
- 手動で監視/実行を停止するにはプロセスに対する通常のシグナル（Ctrl+C 等）を使えます。
- 運用上の停止指示はファイルフラグ方式で行われます:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します。
  - KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で停止処理が行われます（ExecutionEngine は Settings.kill_flag_path を参照している設計）。
- kill.flag は設定次第で起動時に自動クリア（KILL_FLAG_CLEAR_ON_START=1）できますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring ポーリングループ起動スクリプト
  - config.py                       — 環境変数 / 設定取得ユーティリティ
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層（監視ログ）
    - system_monitor.py              — システム / データ鮮度監視
    - risk_monitor.py                — ドローダウン / ポジション上限監視
    - kill_switch.py                  — Kill Switch ファイル書き込み
    - monitoring_engine.py            — 複数 Monitor の束ね
    - ...（TradeMonitor 等の実装が含まれる想定）
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数計算・集約キャップ
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — ファクター計算
    - feature_exploration.py         — 将来リターン・IC 等
  - utils/
    - logging_setup.py               — ログ初期化ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity
    - ...その他ユーティリティ

補足・運用上の注意
-----------------
- KABUSYS_ENV=live モードは実際の発注を行うため、設定（LINE 通知、API パスワード、Kill Switch の設定など）を十分に確認してください。validate_config は本番モード時に追加の警告を出します。
- AI 機能を有効にする場合は OPENAI_API_KEY を用意してください。API 呼び出しはコストが発生します。
- SQLite/DuckDB のファイルはデフォルトで data/ 以下に保存されます。バックアップ・権限設定に注意してください。
- ロギングでファイル出力が失敗した場合はコンソール出力のみで継続する設計になっています。

よく使うコマンド例
------------------
- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Paper Trading レポート作成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ に定義（現状 0.1.0）。  
- ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（この README には記載していません）。

以上がこのコードベースの概要・セットアップ・使い方です。README の補足やコマンド例で不明点があれば、使い方（どの機能を先に試したいか）を教えてください。必要に応じて .env のサンプルや運用手順（デーモン化 / systemd サービス化など）を追記します。