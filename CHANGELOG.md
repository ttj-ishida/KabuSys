CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: 以下はリポジトリ内のソースコード（スクリプト、モジュール、コメント等）から推測して作成した変更履歴です。実際のコミット履歴とは必ずしも一致しません。

Unreleased
----------

- 作業中 / 要注意
  - research/factor_research モジュールは実装途中（関数の続きが切れている）。ファクター計算ロジックの完成とテストが必要。
  - ポートフォリオ構築やポジションサイズ算出のロジックにいくつか TODO コメントあり（価格欠損時のフォールバック、lot_size の銘柄別対応など）。堅牢化・拡張の余地あり。

0.1.0 — 2026-04-19
------------------

Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 と定義。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を利用して実際のブローカークライアント／モックを切り替え。
    - Engine の起動・停止制御（スレッド起動、停止フラグ検出、PID ファイル指定）。
    - プロセス優先度を起動時に "high" に設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル検出による安全停止処理。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。

- 設定管理・CLI
  - config.py: 環境変数・設定取得ユーティリティを追加。
    - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - .env のパースはクォート、エスケープ、コメント、export 形式に対応。
    - 各種プロパティ（DB パス、ログレベル、KABUSYS_ENV、Paper Trading 設定など）を提供。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 標準的な設定項目群（J-Quants、kabu API、DB パス、LINE トークン、ログレベル、Kill Switch 等）を対話形式で生成。
    - 既存 .env の読み込み・マスク表示・保存機能を提供。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在と YAML パース（PyYAML がインストールされていれば検証）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を実装（スコアが全て 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が閾値を超える場合、同セクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。
      - リスクベースの位置サイズ計算、単元株（lot_size）丸め、1銘柄上限・総投下上限（aggregate cap）に基づくスケーリング、cost_buffer の考慮などを実装。
      - 余剰キャッシュで小数端数を lot 単位で追加配分するアルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング初期化ユーティリティを提供。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値対応）。
    - CPU affinity 設定ユーティリティ（psutil を利用）。権限不足や未対応 OS では警告を出してスキップ。

- 監視・モニタリング
  - monitoring_db 初期化呼び出し（run_* スクリプトから呼び出し、監視テーブルが存在することを保証）。
  - run_monitoring のエラーハンドリング: monitor.check_once() で例外が発生してもループ継続しログ出力。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - SQLite（paper_trading.db）からシステム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して標準出力でレポート化。
    - PASS/FAIL 判定基準（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) に対応。
    - P95 計算を内部で実装。

Changed
- 監視動作
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（run_monitoring の設計）。これにより監視データは環境に依存しない単一 DB に集約される。

Fixed
- .env パーサーの耐久性向上
  - export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを明示的に実装。
  - 値のパースに失敗した場合は読み飛ばす等、安全に読み込む動作を提供。

Security
- 機密値の取り扱い
  - config_setup のウィザードでシークレット（トークン・パスワード）をマスク表示し、.env ファイルに明示的に保存する設計を採用（ただし .env を Git にコミットしない旨を強調する注記あり）。

Notes / Limitations
- research/factor_research.py は実装が途中であり、ファクター計算の完成とテストが残っている。
- position_sizing / risk_adjustment 中に価格欠損時のフォールバックや将来的な銘柄別 lot_size への拡張等の TODO コメントが存在するため、実運用前の追加検証を推奨。
- process_priority / cpu_affinity は psutil の機能に依存しており、権限不足や未対応 OS では警告ログを出して設定をスキップする動作。

References
- 各スクリプトの使用例や挙動はソース内の docstring / コメントに記載されています。特に config_setup.py / validate_config.py / tools/paper_verification_report.py は CLI として直接実行可能です。