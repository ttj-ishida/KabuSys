# CHANGELOG

すべての重要な変更履歴はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-18

初回リリース。プロジェクトのコア機能およびユーティリティ、CLI ツール群を追加しました。

### 追加
- 全体
  - 初期パッケージ公開。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 実行 / 監視
  - run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine をデーモンスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）を検知してエンジンを安全停止する仕組みを実装。
    - 起動時に監視テーブルの存在を保証する init_monitoring_db 呼び出しを行う。
  - run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - デフォルト 60 秒のポーリングループで SystemMonitor を定期実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（不正値はデフォルトにフォールバックして警告を出す）。
    - 監視処理は環境にかかわらず本番用 SQLite パス（Settings.sqlite_path）を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了、KeyboardInterrupt による終了にも対応。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env の自動読み込み機構（プロジェクトルートの .env / .env.local をサポート、OS 環境変数を保護）。
    - 必須環境変数取得用の _require、各種設定プロパティ（DB パス、ログレベル、環境判定、paper_trading 用設定など）を実装。
    - `paper_fill_mode` の検証（有効値チェック）、`paper_sqlite_path` の提供。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を作成/更新。多数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH 等）をサポート。
    - 既存値の読み込み、シークレットのマスク表示、保存前の確認を実装。
- 設定検証
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がインストールされている場合）を実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順で上位 N を選定（タイブレークは signal_rank）。
    - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター集中・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: セクター別エクスポージャーを計算し、制限超過セクターの新規候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知値はフォールバック）を提供。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）。
    - calc_position_sizes: risk_based / equal / score の配分法に対応。単元株（lot_size）に丸め、aggregate cap（available_cash 超過時のスケーリング）を実装。コストバッファ考慮の設計。
  - 上記関数群をパッケージエクスポートに登録（src/kabusys/portfolio/__init__.py）。
- ユーティリティ
  - ロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに stdout 出力の StreamHandler と日次ローテーション（30日保持）の TimedRotatingFileHandler を設定。
    - LOG_LEVEL / LOG_DIR 解決ルール、既存ハンドラのクリーンアップ、ディレクトリ作成失敗時のフォールバックを実装。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS の差を吸収してプロセス優先度を設定（psutil を利用）。失敗時は警告でスキップ。
    - set_cpu_affinity で最初の N コアにピン留めする機能を提供（権限やプラットフォームにより安全にフォールバック）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを計算・表示。
    - 閾値（PASS/FAIL 基準）を定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
- 研究 / ファクター計算（着手）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py、作業途中）。
    - モメンタム・ボラティリティ・流動性・バリュー等を DuckDB の prices_daily / raw_financials を参照して計算する方針を実装。
    - calc_momentum の骨格（定数・関数シグネチャ等）を追加（実装途中）。

### 変更
- .env 自動読み込みの挙動
  - プロジェクトルート自動検出を .git または pyproject.toml を基準に実装し、CWD に依存しない読み込みを実現（src/kabusys/config.py）。
  - .env 読み込み時に OS 環境変数を保護する protected 機能を追加（.env.local を override=True で読み込むが OS 環境変数は上書きしない）。
- ログ出力
  - ログハンドラの初期化処理で既存ハンドラを flush/close してから削除するようにして二重設定を防止（src/kabusys/utils/logging_setup.py）。
  - コンソールには stdout を使う方針（cron/Task Scheduler のリダイレクトに配慮）。

### 修正（堅牢性 / エラーハンドリング）
- 環境変数パーサーの堅牢化（src/kabusys/config.py）
  - _parse_env_line でシングル / ダブルクォート内のバックスラッシュエスケープを正しく処理し、インラインコメントを無視する挙動を実装。
  - キー・値の存在チェックや空行・コメント行のスキップを明確化。
- ポーリング間隔の検証（src/kabusys/run_monitoring.py）
  - 環境変数 MONITOR_POLL_INTERVAL が 1 未満や不正な値のときにログ警告しデフォルトにフォールバック。
- DB 周りの耐障害性
  - paper_trading 用と本番用で DB パスを分離。監視テーブルの初期化を冪等に実行してテーブル不在時の失敗を回避。
  - paper_verification_report でテーブル・列が存在しない場合に sqlite3.OperationalError をキャッチしてデフォールト値を扱うようにした（空データ時の安定出力）。
- プロセス優先度 / CPU affinity の失敗時に例外を投げず警告でスキップするようにして、権限不足や未対応プラットフォームで起動が止まらないように改善。

### ドキュメント
- 各モジュールに詳細な docstring と使用法例を追加。主要な CLI スクリプトに使い方コメントを追加（run_*.py、config_setup.py、paper_verification_report.py 等）。
- PortfolioConstruction.md / StrategyModel.md など外部設計文書に準拠する旨を注記（ソース内コメント）。

### 既知の制限 / TODO
- research/factor_research.calc_momentum 等の一部ファクションは実装途中（ファイル末尾で切れている）。DuckDB ベースの計算は概念実装済みだが追加テストと完成が必要。
- position_sizing の lot_size は現状グローバル固定（将来的には銘柄別 lot_map の導入を検討）。
- apply_sector_cap の価格欠損時の挙動に注意（価格 0.0 の場合にエクスポージャーが過小評価される可能性あり。fallback ロジック追加を検討）。

---

このリリースではベースとなるランタイム／運用周り（起動スクリプト、設定管理、ロギング、プロセス制御）、ポートフォリオ構築ロジック、および検証・ツール群を整備しました。以降は research モジュールの完成、戦略コアの統合、E2E テスト、運用時の監視・アラート整備を進めます。