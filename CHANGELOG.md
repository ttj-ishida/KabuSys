Keep a Changelog
=================

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の慣例に従います。  

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0

## [0.1.0] - 2026-04-20

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、検証・レポートツールを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を最初に設定し、スレッドでエンジンを実行。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（`data/paper_trading.db` または環境変数 `PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - 停止フラグ（data/stop_requested.flag）検出時に安全に停止。
    - 実行 PID ファイル (`data/execution.pid`) をサポート。

  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用する設計（監視データは一元管理）。
    - 停止フラグ検知によりループを終了し、DB 接続を確実にクローズ。

- 設定・環境管理
  - config.py
    - .env 自動読み込み (.env → .env.local, OS 環境変数優先) を実装。プロジェクトルートは `.git` または `pyproject.toml` から探索して特定。
    - `.env` パース機能強化：`export KEY=val`、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
    - Settings クラスを追加し、各種環境変数（DB パス、API トークン、モード切替、監視閾値等）をプロパティで提供。
    - `paper_fill_mode` の検証（有効値: "instant"|"partial"|"never"|"reject"）を実装。
    - 環境判定用プロパティ（is_live / is_paper / is_dev）を追加。

  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - 秘匿値マスク、選択肢表示、既存値の読み込み、保存前の確認をサポート。
    - `.env` 書き込みフォーマット（コメント付きテンプレート）を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・YAML パース検証（PyYAML がない場合は警告）を実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティを追加。
    - ログレベルの解決順（関数引数 > 環境変数 `LOG_LEVEL` > デフォルト）とログディレクトリ解決順（引数 > `LOG_DIR` > `logs/`）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX の差分を吸収）。
    - `set_process_priority(level)` で "high"/"normal"/"low" をサポート。未対応 OS や権限不足時は警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)` を追加（最初の N コアに固定、未対応時は警告を出す）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を追加。
    - スコア全てが 0 の場合は等金額配分にフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を追加。既存保有のセクター比率が閾値を超えるセクターの新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を追加（bull:1.0 / neutral:0.7 / bear:0.3）。未知レジームは 1.0 でフォールバックし警告。

  - portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）を追加。allocation_method により "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）に基づく丸め、1銘柄上限、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer（手数料・スリッページ見積）を実装。
    - price 欠損時のスキップやデバッグログを整備。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート作成 CLI を追加。
    - システム安定性（稼働率）、注文成功率（fill rate）、送信率、API レイテンシ（平均 / 最大 / P95）やリスク却下数を計算してレポート出力。
    - P95 算出ユーティリティ、期間フィルタ処理、閾値に基づく PASS/FAIL 判定（デフォルト閾値をソース内に定義）を実装。
    - DB パスは引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルトを優先順で解決。

- データ分析（研究）モジュール
  - research/factor_research.py（基盤実装を追加）
    - モメンタム・ボラティリティ等のファクター計算のための定数と calc_momentum の骨組みを追加（DuckDB 接続を受ける設計）。
    - （注）このファイルの calc_momentum 実装は途中までであり、今後の完成が必要（詳細は Known issues を参照）。

- 監視 DB 初期化
  - monitoring/monitoring_db.py（呼び出し箇所あり）
    - 起動時に監視テーブルの存在を保証する init_monitoring_db を各起動スクリプトから呼び出して冪等に初期化。

### Changed
- ログの標準出力を stdout に統一
  - cron / タスクスケジューラからの起動時に stdout/stderr を一本化して運用しやすくするため、StreamHandler を stdout に設定。

- DB 接続とクリーンアップ
  - run_execution / run_monitoring で sqlite3 / duckdb 接続を取得し、終了時に finally ブロックで確実にクローズするように設計。

- 環境自動読み込みの扱い
  - 自動 .env ロードはデフォルトで有効だが、テスト時や特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

### Fixed
- 不正なポーリング間隔指定の耐性
  - `MONITOR_POLL_INTERVAL` に不正な値が指定された場合、警告を出してデフォルト（60 秒）にフォールバックするように修正（ValueError によるクラッシュを防止）。

- 監視 DB 初期化の冪等性確保
  - run_execution と run_monitoring の起動時に `init_monitoring_db` を呼び出し、監視テーブルが存在することを保証（重複呼び出しでも安全）。

- process_priority の失敗耐性向上
  - 権限不足や未対応 OS では警告を出して処理を続行するようになり、起動失敗につながらないように改善。

### Known issues
- research/factor_research.calc_momentum の実装は途中で中断されています（ファイル末尾で切れている箇所あり）。モメンタム計算の完全な実装は次リリース以降に追加予定です。
- 一部の TODO（例: position_sizing の銘柄別 lot_size サポート、price フォールバックロジック）は将来の機能拡張項目です。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注:
- 上記はソースコードから推測して作成した変更点です。実際のリリースノート作成時はコミット履歴やリリース担当者の確認を推奨します。