# KabuSys

日本株向け自動売買システムのリポジトリ（ライトウェイト版）。  
この README は、コードベース（src/kabusys 以下）の主要コンポーネント、セットアップ、実行方法をまとめたドキュメントです。

注意: 本リポジトリはローカル/ステージング/本番での実行を想定しており、環境変数で挙動を切り替えます。特に本番環境（KABUSYS_ENV=live）では設定を慎重に扱ってください。

概要
----
KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: ブローカー連携による注文管理と発注
- 監視（Monitoring）: システム状態・取引・リスク監視、Kill Switch による自動停止
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限
- 研究（Research）: ファクター計算・特徴量解析（DuckDB を用いたオフライン処理）
- AI 補助: ニュースを LLM（OpenAI）で解析してセンチメント/レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード/検証 CLI
- ツール: ペーパートレード検証用レポート生成

主な特徴
--------
- 環境切替: KABUSYS_ENV により development / paper_trading / live をサポート
- Paper trading と本番 DB の分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を用いた分析向けデータ処理（prices_daily / raw_financials 等）
- OpenAI を使ったニュースセンチメント・レジーム判定（フェイルセーフ設計）
- Monitoring による定期チェック・ログ永続化と自動アラート（Kill Switch）
- 設定ウィザード（対話式 .env 生成）と起動前検証 CLI

セットアップ手順
----------------

1. リポジトリをクローンして依存をインストールします（仮想環境推奨）。

   例:
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   必要な主要パッケージ:
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（config/*.yaml の内容検証に使用）

   注: sqlite3 は Python 標準ライブラリとして同梱されています。

2. .env を作成します（対話式ウィザードを推奨）。

   ```
   python -m kabusys.config_setup
   ```

   ウィザードは以下の主要変数を設定します（抜粋）:
   - KABUSYS_ENV (development | paper_trading | live)
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, デフォルト: data/paper_trading.db)
   - LOG_LEVEL (DEBUG/INFO/...)
   - KILL_FLAG_CLEAR_ON_START (0/1)

3. 設定検証を行います。

   ```
   python -m kabusys.validate_config
   ```

   --strict オプションを付けると警告も失敗扱いになります。

4. データディレクトリとログディレクトリの作成は自動で試みますが、必要に応じて手動で用意してください:
   - data/（sqlite ファイル・フラグファイル等）
   - logs/（ログファイル）

実行方法
--------

主要な起動スクリプトはモジュールとして実行できます。

- 監視ループ（Monitoring）
  - 意味: SystemMonitor を定期ポーリングして system_status 等を記録し、Kill Switch 評価やアラート送出を行う。
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - オプション的挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。1 未満や負は無視されデフォルトにフォールバック。
    - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境にかかわらず）。

  - 終了方法:
    - 停止フラグファイル data/stop_requested.flag を作成するとループは終了します（run_monitoring はこのファイルを監視）。
    - Execution 停止のための Kill Switch は data/kill.flag（Settings.kill_flag_path）を用いる。

- 実行エンジン（ExecutionEngine）
  - 意味: ブローカーとのインタラクションを行い注文を出すメイン実行プロセス
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と完全に分離します。
    - 実行開始時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書き、stop フラグを検知して安全停止します。

- 設定ツール
  - 対話式 .env ウィザード:
    ```
    python -m kabusys.config_setup
    ```
  - 設定検証:
    ```
    python -m kabusys.validate_config [--strict]
    ```

- ペーパートレード検証レポート
  - ペーパートレード用 SQLite を集計して PASS/FAIL レポートを出力します:
    ```
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    ```
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

設定と環境変数（主要）
---------------------
（デフォルト値は .env ウィザードや Settings クラスの docstring を参照してください）

- 必須（起動前に .env を設定すること）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行/挙動制御
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0|1

- データパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時の専用 DB)

- Paper trading
  - PAPER_FILL_MODE: instant | partial | never | reject

- AI（OpenAI）
  - OPENAI_API_KEY を設定しておくと ai.news_nlp や regime_detector で利用可能

- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、環境変数で上書き可能）

停止・Kill Switch の仕組み
------------------------
- run_monitoring / run_execution は data/stop_requested.flag を監視/参照します。管理者がこのファイルを作成するとプロセスが停止や起動抑止を行います。
- Kill Switch（自動停止）は条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグを確認します。
- Kill Switch の評価は MonitoringEngine 内で RiskMonitor/TradeMonitor/SystemMonitor の結果に基づいて行われます（ドローダウン超過やポジション上限など）。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging を用いて統一的に行われます。
- デフォルトでは stdout と logs/<app_name>.log（日次ローテーション）に出力します。
- LOG_DIR 環境変数や setup_logging の引数でログ先を変更できます。

DB スキーマ / 永続化
-------------------
- 監視用 SQLite（monitoring.db）には以下のテーブルが作成されます（init_monitoring_db による自動作成・マイグレーション）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- DuckDB（kabusys.duckdb）は研究/分析用テーブル（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等）を想定
- Paper trading は専用の SQLite に記録され、本番 DB と分離されます

プロジェクトのディレクトリ構成（主要部分）
----------------------------------------
以下は src/kabusys/ 配下の主要なモジュール／サブパッケージと役割の概略です。

- kabusys/
  - __init__.py (バージョンなど)
  - config.py
    - Settings クラス: 環境変数の読み取り・検証、自動 .env ロードロジック
  - config_setup.py
    - .env を対話式に生成するウィザード
  - validate_config.py
    - 起動前に環境と config/*.yaml を検証する CLI
  - run_monitoring.py
    - SystemMonitor をポーリングする監視プロセスのエントリポイント
  - run_execution.py
    - ExecutionEngine の起動エントリポイント（paper_trading の場合はモックブローカー）
  - utils/
    - logging_setup.py: ロギング初期化
    - process_priority.py: プロセス優先度 / CPU affinity 制御
  - monitoring/
    - monitoring_db.py: SQLite による永続化レイヤ（作成・CRUD）
    - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度の監視
    - trade_monitor.py: （未掲示だが）注文滞留・約定異常などを監視する想定
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: フラグファイルによる停止トリガ
    - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py: （未掲示）アラート送信ロジックの想定
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 実際の発注ロジック・ブローカー抽象化・注文状態管理など（詳細は各ファイル）
  - portfolio/
    - portfolio_builder.py: 候補選定、スコアソート、重み付け
    - position_sizing.py: 発注株数計算、lot 単位丸め、aggregate cap
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: モメンタム、ボラティリティ、バリュー等の計算（DuckDB）
    - feature_exploration.py: 将来リターン、IC、統計要約
  - ai/
    - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py: マクロニュース + ETF MA による市場レジーム判定
  - tools/
    - paper_verification_report.py: ペーパートレード DB を集計して検証レポート出力

開発者向けノート
----------------
- DuckDB を使った研究コードは外部にアクセスせずにローカル DB を用いて完結する設計です。テスト時は DuckDB 接続をモックできます。
- OpenAI API 呼び出しはリトライ・バックオフ・レスポンス検証を実装しており、API 失敗時のフェイルセーフ（0.0 で継続）を行います。
- Settings はプロジェクトルート（.git / pyproject.toml）を基準に .env を自動ロードします。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログディレクトリ・データディレクトリへの書き込みに失敗しても（権限等）コンポーネントは可能な限り継続する設計です（ただし本番では適切なディレクトリ権限を確認してください）。

よくある運用フロー（例）
-----------------------
1. .env を作成（config_setup）
2. 設定検証（validate_config）
3. データ取得・DuckDB の初期投入（別スクリプト）
4. run_execution をデーモン起動（systemd / supervisor 等）
5. run_monitoring を別プロセスで起動して定期監視
6. 必要に応じて Kill Switch を監視して自動停止

ライセンス・貢献
----------------
リポジトリに含まれる LICENSE を参照してください。バグ修正や改善提案は Pull Request を歓迎します。

サポート
-------
不明点や問題が生じた場合は、まず `python -m kabusys.validate_config` とログファイルを確認してください。AI 関連やブローカー接続は外部サービス依存となるため、キーや接続先 URL の設定ミスが多い箇所です。

付録: 便利なコマンド一覧
-----------------------
- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- 実行エンジン（paper_trading モードで起動する場合）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

以上。必要があれば README にサンプル .env、systemd ユニットファイル例、CI テストの手順などを追加します。どの情報を優先して追加希望か教えてください。