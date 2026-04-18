KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・リサーチ・監視機能を含む小規模フレームワークです。  
設計方針は「本番と分析／テストを明確に分離」「外部 API 呼び出しは制御可能」「ログ・監視を重視する」ことにあります。

主な機能
-------
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード（KABUSYS_ENV による切替）に対応
  - Paper Trading では MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度設定・PID 管理・停止フラグ監視を実装
- 監視デーモン（SystemMonitor 等）の起動スクリプト（run_monitoring.py）
  - システム負荷・データ鮮度・プロセス生存のポーリング監視
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化
- 監視エンジン（MonitoringEngine）/ 個別モニタ（SystemMonitor, TradeMonitor, RiskMonitor）
  - Kill Switch（条件に応じて data/kill.flag を書き込む）実装
  - AlertManager 経由で通知（LINE 等との接続は環境変数で設定）
- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、重み計算、セクター上限処理、ポジションサイズ計算などの純粋関数群
- リサーチ（research モジュール）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン、IC 計算、統計サマリ
  - DuckDB を利用して prices_daily, raw_financials を参照して計算
- AI モジュール（ai）
  - news_nlp: ニュース記事を OpenAI に投げて銘柄別センチメントスコアを生成し ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ユーティリティ
  - ログ設定（utils/logging_setup.py）: stdout と日次ローテーションログを統一的に設定
  - プロセス優先度/CPU affinity 設定（utils/process_priority.py）
- CLI 補助スクリプト
  - config_setup.py: .env 対話式ウィザードで初期設定を生成
  - validate_config.py: 環境変数 / config/*.yaml の存在・整合性チェック
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポート出力

動作要件（推奨）
--------------
- Python 3.10+（型アノテーションの記法により）
- 必要な外部パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証用、オプション）
- SQLite（標準ライブラリで提供）
- ネットワーク接続（OpenAI / 各種 API を利用する機能を使う場合）

インストール（例）
-----------------
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨します。

初期設定 (.env)
----------------
プロジェクトルートに .env を置くと自動で読み込まれます（.env.local を上書きして読み込む仕様）。  
自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

対話式生成:
- python -m kabusys.config_setup
  - J-Quants / kabuAPI トークン、DB パス、KABUSYS_ENV 等を対話式に設定して .env に保存します。

設定検証:
- python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit(1)

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
  - paper_trading: 発注はモック・DBは data/paper_trading.db に分離
- DUCKDB_PATH: duckdb ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring が参照、デフォルト 60）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- PID_FILE_PATH, KILL_FLAG_PATH: PID / Kill Flag のパス
- KILL_FLAG_CLEAR_ON_START: 起動時に既存の Kill Flag を自動クリアするか（開発時のみ注意）

実行方法（基本）
--------------
- 監視デーモン起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（例: MONITOR_POLL_INTERVAL=30）

  実装メモ:
  - run_monitoring は常に settings.sqlite_path（本番 path）を使用して監視ログを記録します。
  - 起動時に process priority を high に設定し、stop_requested.flag の存在でループを終了します。

- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBroker を利用します。

  実装メモ:
  - 起動前に data/stop_requested.flag が存在すると起動を行わず終了します。
  - エンジンは別スレッドで run_session を実行し、stop_requested.flag の検知で停止を指示します。

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - DB を指定しない場合は環境変数 PAPER_TRADING_SQLITE_PATH → data/paper_trading.db を参照

- AI スコアリング / レジーム判定:
  - ai モジュールの関数はプログラムからインポートして使用します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。  
  - 実行には OPENAI_API_KEY が必要です。失敗時はフェイルセーフ（既定値やスキップ）で継続する設計です。

監視 / 停止フラグ
-----------------
- 停止要求（run_monitoring / run_execution の外部停止）:
  - data/stop_requested.flag を作成すると両スクリプトは終了検知します（run_monitoring はループ中に検知、run_execution はスレッド実行中に検知して engine.stop() を呼びます）。
- Kill Switch:
  - KillSwitch は監視ロジックの結果に応じて data/kill.flag を書き、実行エンジンに停止を促すために利用します（Settings.kill_flag_path でパス指定可能）。

データベース（監視）スキーマ
--------------------------
init_monitoring_db() により次のテーブルが作成されます（冪等）:
- system_status (cpu, memory, disk, process_ok, recorded_at)
- trade_logs (注文イベント履歴、latency_ms カラムあり)
- positions
- risk_logs
- dashboard (id=1 の単一行に集計を保持)

ディレクトリ構成（src/kabusys の主要ファイル）
----------------------------------------
- kabusys/
  - __init__.py
  - config.py               — Settings / .env 自動読み込みロジック
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在する場合)
  - utils/
    - logging_setup.py
    - process_priority.py

設計上の注意点 / 運用メモ
------------------------
- 環境分離:
  - paper_trading モードは本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- ログ:
  - setup_logging() によりコンソール（stdout）とファイル（logs/<app>.log）に出力します。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- OpenAI 関連:
  - news_nlp / regime_detector は OpenAI を呼び出します。レスポンスのバリデーションやリトライを実装しており、API 失敗時はフェイルセーフ（スコア 0.0 や処理スキップ）で続行します。
- テスト容易性:
  - OpenAI 呼び出し部分は内部で関数分離されており、unittest.mock.patch で差し替えてテスト可能です。
- 設定検証:
  - validate_config.py は .env の必須設定や config/*.yaml の存在（PyYAML がインストールされている場合はパース検証）を確認します。

よく使うコマンドまとめ
--------------------
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 監視起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- ライブラリ関数呼び出し（例）
  - Python スクリプト内から import kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime

最後に
------
この README はコードベースの参照ドキュメントです。運用前に必ず python -m kabusys.validate_config を実行して設定の整合性を確認してください。実運用（KABUSYS_ENV=live）の際は Kill Switch 設定や LINE 通知先などのアラート周りを厳密に設定してください。問題や改善提案があればコード内コメントや設計注記を参照のうえ PR をお願いします。