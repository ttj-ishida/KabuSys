CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。
このファイルはプロジェクトのリリース履歴を日本語でまとめたものです。

フォーマット:
- 変更種別: Added / Changed / Fixed / Deprecated / Removed / Security
- 各項目は簡潔に何を追加・変更したかを記載します。

## [Unreleased]

（現在未リリースの変更はここに記載します。現時点では特記事項なし。）

## [0.1.0] - 2026-04-19

初期リリース。システム全体の起動スクリプト、設定管理、モニタリング、実行エンジン、ポートフォリオ構築ロジック、ユーティリティおよび検証/セットアップ用 CLI を含む基本機能を実装しました。

Added
- コアパッケージ初回導入
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）でポーリング間隔を上書き可能。0 以下や不正値はデフォルトにフォールバックして警告を出力。
    - 監視モジュールは環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用して監視 DB に接続。
    - stop_requested.flag を検知して安全にループ終了。
    - duckdb 接続の併用。
  - run_execution.py
    - ExecutionEngine（注文エンジン）起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む想定）。
    - ExecutionEngine を別スレッドで実行し、stop_requested.flag による停止処理を実装。
    - 起動時に execution.pid を扱う仕組みを用意。
- 設定管理
  - config.py
    - Settings クラスを提供し環境変数をプロパティ経由で取得。主要プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
      - KABUSYS_ENV（development|paper_trading|live の検証）
      - LOG_LEVEL（有効値検証）
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - paper_fill_mode（"instant"|"partial"|"never"|"reject" の検証）
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）を実装し、.env/.env.local を自動読み込み（OS 環境変数の保護を考慮）。
    - .env のパースは quote/escape、export プレフィックス、インラインコメントを考慮。
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを実装。デフォルト値、選択肢、シークレット入力に対応。
    - 生成される .env のテンプレート内容を定義。
  - validate_config.py
    - 起動前設定検証 CLI を実装。.env の必須キー、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス、config/*.yaml の存在と（可能なら）パース検証を行う。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番（live）環境向けのガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を実装。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - シグナルの候補抽出（スコア降順・タイブレーク）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 のとき等配にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap（売却予定銘柄除外、"unknown" セクターは制限免除）。
    - レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバックして警告）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes。allocation_method により risk_based / equal / score をサポート。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮したスケーリング実装。
    - 価格欠損時の安全処理とログ出力を備える。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的ロギング初期化関数 setup_logging を追加。stdout ストリームハンドラ + 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の環境変数や引数からの上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX の差分を吸収してプロセス優先度を設定。AccessDenied 等は警告にしてスキップ。
    - set_cpu_affinity(cpu_count) による CPU ピンニングを提供（未対応時は警告）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。指定期間の system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95含む）を算出し PASS/FAIL 判定を出力する。
    - P95 計算、閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）を定義。
    - --from/--to/--db オプションをサポート。
- リサーチ（骨格）
  - research/factor_research.py（ファクター計算モジュールの骨格）
    - DuckDB を使ったモメンタム、Value、Volatility、Liquidity 等のファクター算出方針とユーティリティを用意。（将来的な拡張のための設計・定数が定義済み）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数ファイル .env の取り扱いに関して README にコミットしない旨を強調するテンプレートを config_setup で出力。
- シークレット値は対話ウィザードでマスク表示する等の配慮あり（ただし運用上の注意はドキュメント参照）。

Notes / 補足
- .env の自動ロードはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。
- monitoring 系は設定に依らず監視 DB（SQLITE_PATH）を使用する設計とし、paper_trading の DB 分離を保証。
- run_monitoring/run_execution は起動直後にプロセス優先度を "high" に設定する処理を含む（権限が不足する場合は警告を出しスキップ）。
- DuckDB と SQLite を併用する設計になっており、分析系は DuckDB、軽量の事象記録や監視は SQLite を想定。
- research/factor_research.py はモジュール設計の主要部分を含むが、実装の続きや最終的な SQL/処理は今後の拡張対象。

作者連絡・貢献
- 変更やバグ報告、提案はリポジトリの Issues にてお願いします。

（以降のバージョンはここに追加していきます）