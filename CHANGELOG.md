CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
このプロジェクトの現在のバージョンは src/kabusys/__init__.py の __version__ を参照してください。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

Added
- 初回公開: KabuSys 自動売買フレームワークの初期実装を追加。
  - 基本 CLI / ランチャー
    - python -m kabusys.config_setup: 対話式 .env 設定ウィザードを追加。既存値の読み込み／マスク表示、確認後 .env 書き込み機能を提供。デフォルト値や選択肢を定義済み。
    - python -m kabusys.validate_config: 起動前設定検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config/*.yaml の存在とパース検証、KABUSYS_ENV=live 時の追加ガードなどを実行。--strict オプションで警告も失敗扱いにできる。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を高に設定し、Broker クライアントの生成、OrderRepository/OrderManager/ RiskManager/Reconciler の組み立て、エンジンのスレッド実行・停止フラグ処理を行う。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検知、例外を捕えて次ポーリングへフォールバック。
  - 設定・環境管理
    - Settings クラスを追加。環境変数の取得・検証を一元化（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）と閾値（CPU/MEM/DISK）をプロパティで提供。
    - 自動 .env ロード機能: プロジェクトルート (.git または pyproject.toml) を探索して .env を自動読み込み。OS 環境変数は上書きされない（保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを無効化可能。
    - .env パーサーを強化: export KEY=val 形式に対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォートなしの場合は直前がスペース/タブの '#' をコメントと認識）などをサポート。
  - ポートフォリオ構築（純関数群）
    - portfolio.select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - portfolio.calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み付け関数。スコア合計が 0 の場合は等金額へフォールバック。
    - portfolio.calc_position_sizes: allocation_method (risk_based / equal / score) に基づく株数算出。lot_size（単元）丸め、max_position_pct・max_utilization による制約、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した実装。
    - portfolio.apply_sector_cap: セクター別エクスポージャーを計算し、セクター上限を超える銘柄の新規候補を除外（"unknown" セクターは除外対象外）。
    - portfolio.calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告のうえ 1.0 にフォールバック）。
  - 研究モジュール
    - research.factor_research: DuckDB の prices_daily / raw_financials を用いたファクター計算を追加（モメンタム: 1M/3M/6M/MA200乖離、ボラティリティ: ATR/平均売買代金 等）。関数は DuckDB 接続を受け取り、(date, code) キーの dict リストを返す設計。
  - ユーティリティ
    - utils.process_priority: set_process_priority および set_cpu_affinity を追加。Windows / POSIX の違いを吸収し、権限不足や未対応環境では警告を出してスキップする堅牢な実装。
  - Paper Trading / 検証
    - tools/paper_verification_report.py: Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成するツールを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値に基づく PASS/FAIL 判定を行う。デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms。
  - DB 初期化
    - run_* スクリプトで監視テーブルの初期化を行うための init_monitoring_db 呼び出しを導入（冪等的にテーブル存在を保証）。

Changed
- 実行時挙動・設計上の重要点（注意点）
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path (Settings.sqlite_path) を使用して監視データを記録する設計。環境区別を期待する場合は注意が必要。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper 用専用 SQLite (Settings.paper_sqlite_path、デフォルト data/paper_trading.db) を使用して本番 DB と完全に分離する動作を採用。paper_trading では MockBrokerClient が使用される想定。
  - 起動時にプロセス優先度を "high" に設定する処理を両ランチャーで最初に実行するようにした（set_process_priority 呼び出し）。
  - 停止制御はプロジェクト内 data/stop_requested.flag (または設定された kill_flag_path) によるファイルフラグで行う設計。kill flag の自動クリアは KILL_FLAG_CLEAR_ON_START で制御可能で、本番では 0 を推奨。
  - MONITOR_POLL_INTERVAL 環境変数を追加（監視ポーリング間隔の上書き、デフォルト 60 秒）。0 以下や不正値は警告後にデフォルトへフォールバック。

Fixed
- 環境ファイルの読み込みでの堅牢性向上:
  - ファイル読み込み失敗時に警告を出してスキップするようにした。
  - .env 行パーサーのバグ回避（export 接頭辞、クォート内のエスケープ、インラインコメント処理などを改善）。
- validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告を出す処理を追加し、YAML が存在しない場合の案内メッセージを改善。
- calc_score_weights / calc_regime_multiplier 等で不定値（0 など）に対するフォールバックと警告を追加し、安全性を向上。

Security
- .env の扱いに関する注意喚起を config_setup の出力に追加（.env を Git にコミットしない旨の警告を出力）。
- Settings._require は必須環境変数未設定時に ValueError を投げ、起動前に致命的な設定漏れを検出するようにした。

Notes / Migration
- 本番／ペーパー用 DB の取り扱いに注意:
  - 監視（run_monitoring）は本番 sqlite_path（SQLITE_PATH）を参照するため、ペーパートレードの監視データを分離したい場合は運用側で適切にパスを設定／スクリプトを修正してください。
  - ペーパートレード実行（run_execution）は paper_trading モードで paper_sqlite_path を使用するため、本番 DB への誤書き込みは避けられる設計です。
- プロセス優先度設定や CPU affinity は権限不足・未対応 OS では例外を握り潰して警告する実装です。必要に応じて実行環境の権限を確認してください。
- validate_config で config/*.yaml の検証を行うので、設定ファイルを利用する場合は PyYAML のインストールを推奨します。

今後の予定（例）
- ファクター計算・ポートフォリオ構築の単体テスト充実化。
- 銘柄ごとの lot_size をサポートする拡張（stocks マスタの導入）。
- run_monitoring/run_execution の systemd / supervisor 用ユニット例の追加。
- monitoring_db / SystemMonitor / ExecutionEngine の詳細ログ・メトリクス強化。

-----