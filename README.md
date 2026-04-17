# KabuSys — README

このリポジトリは日本株向けの自動売買・解析プラットフォームの一部です。ここではリポジトリ内の主要な機能と使い方、セットアップ手順、ディレクトリ構成を日本語でまとめます。

概要
- KabuSys は日本株の自動売買（ExecutionEngine）、監視（Monitoring）、リサーチ（ファクター計算・特徴量解析）、ポートフォリオ構築、AI ベースのニュース解析などを含むモジュール群です。
- 本 README は提供されたコードベース（src/kabusys 以下）を対象にした導入・運用ガイドです。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード（KABUSYS_ENV=paper_trading）に対応。
  - paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離。
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による安全停止、PID ファイル（data/execution.pid）管理。

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク使用率、Execution プロセスの監視、データ鮮度チェック。
  - TradeMonitor: 注文滞留（stale orders）、約定価格異常（price anomaly）監視。
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボードの更新、リスクイベント記録。
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止信号を送る。
  - MonitoringEngine: 上記モニタをまとめて周期的にポーリング、アラート通知（AlertManager を介した通知）を行う。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。なお monitoring は常に settings.sqlite_path（本番パス）を使用する。

- 環境設定 / 検証
  - config_setup.py: 対話式ウィザードで .env を作成 / 更新。
  - validate_config.py: .env と config/*.yaml の存在や基本的妥当性を検証（--strict で警告を FAIL 扱いにできる）。

- リサーチ（research パッケージ）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクターを DuckDB 上で計算。
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、基本統計サマリ。

- ポートフォリオ（portfolio パッケージ）
  - 候補選定、等重・スコア重み付け、セクターキャップ適用、ポジションサイズ計算（lot 単位丸め・集約キャップ対応）等。

- AI（ai パッケージ）
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書込む。バッチ処理・リトライ・レスポンス検証あり。
  - regime_detector: ETF（1321 等）の MA 乖離とマクロニュース LLM スコアを合成して market_regime を判定・永続化。

- ツール
  - tools/paper_verification_report.py: ペーパートレード結果を集計し PASS/FAIL 判定のレポート出力（--from/--to/--db オプション対応）。

セットアップ手順（ローカル開発向け）
1. Python 環境
   - Python 3.9+ を推奨（ソースは型ヒントで 3.10 等を想定）。
2. 依存ライブラリのインストール（最低限）
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を有効にする場合: pip install PyYAML
   - 実運用で必要な他の内部モジュール（broker client 等）がある場合はその依存もインストールしてください。
   - （注）requirements.txt は提供されていないため、プロジェクト固有の追加依存は別途管理してください。

3. 環境変数 / .env の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成。最低必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な環境変数（代表例とデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト） — Monitoring が参照
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時に使用）
     - LOG_LEVEL: INFO（デフォルト）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 動作モード、デフォルト instant）
     - KILL_FLAG_CLEAR_ON_START: 0 | 1（起動時に kill.flag を自動クリアするか）
     - OPENAI_API_KEY: OpenAI API を使う機能（ai/news_nlp, ai/regime_detector）で必要
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（run_monitoring 用、デフォルト 60）
     - KILL_FLAG_PATH / PID_FILE_PATH は Settings でオーバーライド可能（デフォルト data/kill.flag, data/execution.pid）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにできます。

使い方（主要なコマンド）
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番または paper_trading）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB に記録（本番 DB と分離）。
    - 停止は data/stop_requested.flag を作成するか、data/kill.flag があれば起動を回避 / 停止する。
    - プロセス優先度を High に設定しようとします（psutil の権限に依存）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に settings.sqlite_path（本番 sqlite_path）を利用します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD （開始日）
    - --to YYYY-MM-DD （終了日）
    - --db PATH （SQLite DB パス、環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（ライブラリ API）
  - news_nlp.score_news(conn, target_date, api_key=None) — ai_scores テーブルへ書き込む。API キーは引数または環境変数 OPENAI_API_KEY で指定。
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルを更新。
  - これらは CLI ではなく Python API として呼び出します（バッチスクリプト等から利用）。

監視 / 停止関連の挙動
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring のループで存在チェックされており、存在するとループを終了します（グレースフル停止）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch が条件（ドローダウン超過やポジション上限超過）に応じて書き込むと、ExecutionEngine に停止を促します。起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動削除されます（本番では 0 推奨）。
- PID ファイル（data/execution.pid）
  - ExecutionEngine 実行時に書き込み、SystemMonitor は PID ファイルの存在とプロセス存否をチェックします。stale PID は削除され、リスクイベントとして記録されます。

データベース（DuckDB / SQLite）
- DuckDB（分析用）: default data/kabusys.duckdb
  - research / ai の大規模データ・価格テーブル等を格納・参照する想定。
- SQLite（監視・注文履歴）: default data/monitoring.db
  - monitoring_db.init_monitoring_db(conn) によりテーブルと簡易マイグレーションが実行されます。
- Paper trading 用 SQLite: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

注意事項 / トラブルシューティング
- .env は絶対にリポジトリにコミットしないでください（config_setup でも注意喚起あり）。
- OpenAI を使う機能は OPENAI_API_KEY が必要です。API 呼び出しはネットワーク状況やレート制限により失敗するため、実装はエクスポネンシャルバックオフやフォールバック（失敗時は中立スコア等）を行います。
- validate_config は PyYAML がない場合、config/*.yaml の中身検証をスキップします（警告）。
- psutil によるプロセス優先度設定や cpu_affinity の設定は OS と権限に依存します。権限不足の場合は警告を出してスキップします。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                  — Settings（環境変数読み込み・自動 .env ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（テーブル作成・Migration 含む）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （アラート通知ロジック、実装ファイルは存在）
  - execution/                  — Execution 周り（order_manager, broker_factory 等）※一部ファイルは参照のみ
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - order_record.py
  - data/                       — （想定）データ関連モジュール（DuckDB パイプライン等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

追加情報（実装上の留意点）
- 多くの関数は「ルックアヘッドバイアス」を避けるために datetime.today() / date.today() を直接参照しない設計や、duckdb のクエリで target_date 以前のデータのみを使用する等の設計考慮がされています。
- DB 書き込み処理は冪等性や部分的失敗で既存データを保護する工夫（DELETE 対象を限定してから INSERT、executemany の空リスト回避など）が取り入れられています。
- AI 呼び出し周りはレスポンス検証・スコアクリッピング・リトライ処理・部分失敗時の保護などフェイルセーフ設計になっています。

ライセンスやバージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 "0.1.0"）。

以上がこのコードベースの README 相当のドキュメントです。必要であれば運用手順（systemd / supervisor 用のサービスファイル例、ログローテーション、バックアップ、テスト方法）の追記や、ExecutionEngine / Broker の詳細設計ドキュメントを作成します。どの情報を優先して追加しましょうか？