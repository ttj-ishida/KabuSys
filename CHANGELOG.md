# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

- リリース日: 2026-04-18
- バージョン: 0.1.0

## [0.1.0] - 2026-04-18

### Added
- 全体
  - プロジェクト初期実装を追加。モジュール構成、CLI スクリプト、ユーティリティ、ポートフォリオ構築ロジック、検証ツールなどを含む初期機能群を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - ExecutionEngine・OrderManager・RiskManager・Reconciler 等の依存コンポーネントを組み立て、デーモンスレッドで実行。
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に立っていれば起動せず終了。
    - PID ファイル（data/execution.pid）サポート。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視では環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
    - check_once() 実行での例外を受け止めログ出力し、次ポーリングに継続。

- 設定管理
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local、OS 環境変数を保護）。
    - .env の行パーサーは `export KEY=..`、クォート文字列、インラインコメントなどに対応。
    - Settings クラスで各種設定プロパティを提供（DB パス、LINE トークン、閾値、環境判定メソッド等）。
    - `paper_fill_mode` 等の値検証を実装。

  - config_setup.py: 対話式 .env ウィザードを実装。
    - 既存 .env 読み込み、シークレットのマスク表示、選択肢/デフォルトの提示、保存前の確認を提供。
    - .env のテンプレートを書き出すヘッダ付きライター実装。

  - validate_config.py: 設定検証 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML がある場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - live 環境用の追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の警告等）。

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler（cron 等で stdout/stderr をまとめる運用を想定）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラのクリア処理やログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を実装。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows・POSIX（Linux/Mac/FreeBSD）差分を吸収して nice / priority クラスを設定。
    - アクセス権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity() により最初の N コアへプロセスをピンニング可能（例外処理あり）。

- ポートフォリオ / ポジション決定
  - portfolio/portfolio_builder.py:
    - select_candidates(): BUY シグナルのスコア降順ソート（スコア同点は signal_rank でタイブレーク）。
    - calc_equal_weights(), calc_score_weights(): 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックして警告。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクターごとの既存エクスポージャが最大比率を超える場合、新規候補を除外するロジック。
      - "unknown" セクターは上限チェックを適用しない仕様。
      - 当日売却予定銘柄を除外して計算するオプションを提供。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装。未知レジームはフォールバックで 1.0。

  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
      - risk_based: 損切り幅・リスク許容率からベース株数を計算。
      - equal/score: 重み・max_utilization を使って目標株数を算出。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料/スリッページの保守見積）対応。
      - スケールダウン時に残差を lot 単位で補正するアルゴリズムを実装。

- リサーチ / ファクター
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム・ボラティリティ等を計画）。
    - DuckDB 接続を受ける設計、prices_daily / raw_financials テーブルのみ参照する方針を採用。
    - P95 計算や各種期間定数が定義済み（実装はモメンタム等の関数開始）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート出力ツールを追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL）を行う。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成立率(Fill) >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from/--to）と --db オプションをサポート。
    - P95 の計算実装と、データ不足に対する N/A 表示を実装。

- その他
  - monitoring_db などの初期化関数参照を追加（init_monitoring_db を起動時に呼び出し、監視テーブルの存在を保証）。

### Changed
- ロギングのデフォルト挙動
  - ログのコンソール出力を stderr ではなく stdout に統一。cron / Task Scheduler でのリダイレクト運用を想定。
- 環境変数の自動ロード順序の明確化
  - OS 環境変数を保護しつつ .env → .env.local を読み込み、.env.local は override=True で上書き可能にした。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- run_monitoring の挙動
  - 監視は KABUSYS_ENV の値にかかわらず「本番 sqlite_path」を使用する仕様を明記（監視データの一元化を目的とした設計）。

### Fixed / Robustness
- config._parse_env_line: .env パースの堅牢性を向上（export prefix、クォート文字列のエスケープ処理、インラインコメントの扱いなどを考慮）。
- run_monitoring._get_poll_interval: MONITOR_POLL_INTERVAL に不正値（非数・0・負数）が指定された場合にデフォルト（60 秒）へフォールバックし、警告ログを出すようにした（time.sleep に不正値が渡るのを防止）。
- utils/process_priority: 未対応 OS や権限不足での例外をキャッチして警告し、プロセスが異常終了しないようにした。
- utils/logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力のみで継続するよう改善。

### Security
- config_setup ウィザードと .env 書き込み時にシークレット項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE トークン等）を対話中はマスク表示（画面表示のみ）。.env ファイル生成時に注意書きを追加（.env を Git にコミットしない旨の警告）。

### Notes / Known limitations
- research/factor_research.py は設計方針および定数を定義済みだが、モメンタム計算の実装途中（ファイル末尾で関数実装が開始されているように見える）。今後の実装継続が必要。
- position_sizing の lot_size は全銘柄共通設計。将来的には銘柄別単元対応（stocks マスタ参照）への拡張を予定。
- apply_sector_cap で price_map に 0.0 が渡る場合、エクスポージャが過少見積りされる可能性がある旨の TODO コメントあり。フォールバック価格の導入を検討中。

---

上記はソースコードから推測してまとめた初期リリースの変更点一覧です。詳細な使い方やさらに細かな設計決定（Engine の設定値、RiskManager のパラメータ、DB スキーマ等）はプロジェクトのドキュメントや該当モジュールの docstring を参照してください。