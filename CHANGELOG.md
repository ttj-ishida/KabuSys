# Changelog

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Deprecated / Security: 必要に応じて

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-23
初回リリース。自動売買システム KabuSys の基本コンポーネントを実装しました。

### Added
- 全体
  - パッケージの初期バージョンをリリース（__version__ = 0.1.0）。
  - プロジェクトの標準的なログ設定、プロセス優先度設定、環境設定ロード処理などのユーティリティを追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading と本番の DB 分離を実装。paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全な停止処理、PID ファイル出力をサポート。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor（監視ループ）を起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず「本番」用 sqlite_path を使用する設計。
    - 停止フラグファイル検知、例外発生時のロギングとリトライ、プロセス優先度設定を実装。

- 設定周り
  - config.py
    - 環境変数読み込み・設定管理クラス Settings を実装。
    - プロジェクトルート自動検出（.git / pyproject.toml を基準）に基づく .env 自動読み込み機能（.env → .env.local、OS 環境変数は保護）を実装。
    - .env のパースは export 形式、クォート、インラインコメント等に対応。
    - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）や監視／閾値設定、ログレベル、環境モード（development/paper_trading/live）の検証ロジックを実装。
    - Settings のプロパティ経由で型変換・バリデーションを行う設計。

  - config_setup.py
    - 対話式ウィザードで .env を作成／更新する CLI を実装。
    - J-Quants や kabuAPI、DB パス、ログレベル、Kill Switch 設定など主要項目を対話で入力・保存可能。
    - 既存 .env の読み込みと既存値の再利用、シークレット項目のマスク表示等に対応。

  - validate_config.py
    - 起動前の設定検証用 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在確認／YAML パース（PyYAML 利用、存在しない場合は警告）を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定。
    - ログディレクトリ自動作成。作成失敗時はファイルハンドラを無効化してコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py
    - Windows と POSIX（Linux/macOS 等）を吸収するプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity 設定ユーティリティ（指定コア数でプロセスを固定）を追加。
    - 権限不足や未対応プラットフォームでは安全にスキップするハンドリングを実装。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N 件選定。
    - calc_equal_weights: 等金額配分の重みを計算。
    - calc_score_weights: スコア正規化による重み計算（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（既存ポジションのセクター比率が上限を超える場合は同セクターの新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未定義レジームは警告後フォールバック 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出を実装。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）等を考慮した集約キャップ（aggregate cap）とスケーリングロジックを実装。
    - price 欠損や 0 のハンドリング、現保有の差分計算、スケールダウン時のロット単位での再配分を実装。

- 研究・ツール
  - research/factor_research.py
    - ファクター（Momentum / Value / Volatility / Liquidity）計算モジュールの骨格を実装。DuckDB 経由で prices_daily / raw_financials を参照して計算する設計。
    - モメンタム指標（1M/3M/6M リターン、MA200 乖離）や ATR、出来高系指標等を計算する方針を実装（初期実装）。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを実装。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等を SQLite のトレード／監視ログから集計し、PASS/FAIL 判定を出力。
    - コマンドライン引数で期間指定（--from / --to）や DB パス（--db）を指定可能。
    - デフォルト閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。

- データベース関連
  - 監視用 DB 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring から呼び出してテーブル存在を保証（冪等）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- 環境変数の自動読み込みはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB に対して常に prod 用 sqlite_path を使う設計です（監視は環境に依存しない想定）。
- ログは標準出力（stdout）に出力する設計のため、cron 等で stdout/stderr をリダイレクトする運用に適しています。
- process_priority や CPU affinity の設定は実行環境の権限や OS に依存するため、実行時に失敗した場合は警告を出して継続します。

### Known limitations / Future work
- factor_research の詳細実装（各ファクターの SQL / 集計ロジック）は引き続き実装・テストが必要（本リリースでは骨格と一部定数を提供）。
- position_sizing の lot_size は現状グローバル固定。将来的に銘柄毎の単元情報を取り込む拡張を予定。
- 一部のファイル操作や DB 周りで例外時のリカバリやリトライは限定的。運用での実装強化が想定されます。

---

（この CHANGELOG はコードから推測して作成したものであり、実際のコミット履歴に基づくものではありません。必要があれば改訂・詳細化してください。）