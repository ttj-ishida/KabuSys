# Changelog

すべての主要変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21
初回リリース

### Added
- 実行・監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を最初に "high" に設定し、PID ファイル / 停止フラグに対応。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - スレッドでエンジンを実行し、停止フラグ検知で安全に停止する実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視 DB の初期化を行う）。
    - 停止フラグの検知、例外キャッチとログ出力、SQLite / DuckDB のクローズ処理を含む堅牢なループ実装。

- 設定管理・検証・セットアップ関連の追加
  - config.py
    - 環境変数・.env 読み込み機能を提供する Settings クラスを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（優先順位: OS 環境 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパース処理は export プレフィックス、クォート、エスケープ、インラインコメントを考慮して堅牢に処理。
    - 各種設定プロパティを提供（J-Quants、kabuAPI、LINE、DuckDB/SQLite パス、paper_trading 用パス、PID/kill flag、閾値など）。
    - PAPER_FILL_MODE の検証（有効値: instant, partial, never, reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML があればパース検証を実行。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。
    - 秘匿項目は表示時マスク、既存 .env の読み込みと Enter で再利用、入力キャンセル時の挙動、保存時の注意書きを実装。
    - 書き込みフォーマットは .env を Git にコミットしないよう強調するテンプレートを生成。

- ポートフォリオ構築 / ポジション算出ロジック
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank をタイブレーク）、等金額配分、スコア加重配分を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（当日売却予定銘柄はエクスポージャー計算から除外、unknown セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピングおよび未知レジーム時のフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を実装。allocation_method（risk_based / equal / score）に応じた株数算出、単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）でスケールダウンするロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した安全側見積り、スケールダウン時の残差配分ロジックを備える。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite の検証レポート生成スクリプトを追加。システム稼働率、注文成功率（fill/send）、リスクによる却下数、レイテンシ（avg/max/P95）を算出して基準値と比較し PASS/FAIL を判定。
    - P95 計算ユーティリティ、期間フィルタ、DB 存在チェック、SQL 実行時の OperationalError に対するフォールバックを実装。

- ユーティリティ改善
  - utils/logging_setup.py
    - 全アプリケーションで共通利用するロギング初期化ユーティリティを追加。stdout へ出力する StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。既存ハンドラのクリーンアップやログレベル解決ロジックを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - Windows/Linux/macOS を吸収するプロセス優先度設定関数 set_process_priority を追加。psutil を利用し OS ごとの優先度／nice 値を適用、権限不足時は警告でスキップ。
    - set_cpu_affinity による CPU affinity 固定機能を追加（指定なしは変更しない、未対応環境は警告）。
  - DuckDB 統合
    - 複数のモジュールで DuckDB 接続を受け取って分析処理を行う設計を採用（duckdb パッケージを使用）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- なし（初版のため該当なし）

### Fixed
- なし（初版のため該当なし）

### Security
- .env を生成するテンプレートおよび config_setup において「.env を Git にコミットしないこと」を明記。
- Settings._require() は未設定の必須環境変数を ValueError で明示的に失敗させることで、起動時に秘密情報が無い状態での実行を防ぐ。

### Notes / Implementation details
- .env パーサは export 文やクォート、バックスラッシュエスケープ、インラインコメント等に対応しており、実運用でありがちな .env 記述の揺らぎに対して堅牢化しています。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。1 秒未満や不正な値はデフォルト（60 秒）にフォールバックして警告を出します。
- run_execution は paper_trading 時に本番 DB を直接触らないように設計されており、paper_trading 用 DB パスは環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能です。
- portfolio / position sizing 実装は将来的な拡張（銘柄別の lot_size や前日終値フォールバック等）を考慮した設計コメントを含んでいます。

もし特定ファイルごとの変更点や、追加で追記したいリリースノート（例: バグ修正の詳細、既知の制限など）があれば教えてください。適宜追記・整形します。