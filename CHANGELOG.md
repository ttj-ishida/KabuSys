# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

- リリース日付は ISO 8601 形式 (YYYY-MM-DD) を使用しています。
- 重要な設計上の注意点や将来の改善予定も併記しています。

## [Unreleased]

- （現時点のスナップショットでは未リリースの変更はありません）

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用することを明示。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用の分離された SQLite（data/paper_trading.db）を利用。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイル管理。

- 設定管理
  - config.py
    - Settings クラスを提供し、環境変数経由で各種設定を取得（DB パス、API トークン、しきい値など）。
    - 自動 .env ロード機能（.env → .env.local、OS 環境変数優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env 行パーサは `export` プレフィックス、クォート文字列（バックスラッシュエスケープ対応）、インラインコメントの取り扱いなどに対応。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）をサポート。

  - config_setup.py
    - 対話式ウィザードにより .env の初期作成・更新を行う CLI を追加。
    - サンプル項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、ログレベル、Kill Flag 設定など）をサポート。
    - 生成される .env テンプレートは Git にコミットしない旨の注意を含む。

  - validate_config.py
    - 起動前検証 CLI を追加（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml 等の有無／パース検証）。
    - `--strict` オプションで警告をエラー扱いにできる。
    - PyYAML の有無に応じて YAML の検証をスキップ／実行。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout） と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - ログレベル解決（引数 > 環境変数 LOG_LEVEL > デフォルト）、ログディレクトリ解決（引数 > LOG_DIR > logs/）を実装。
    - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。
  - utils/process_priority.py
    - psutil を用いてプラットフォーム差分を吸収したプロセス優先度設定を提供（Windows と POSIX の対応）。
    - CPU アフィニティ設定ヘルパーも追加。

- ポートフォリオ構築・リスク制御・サイズ決定
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全体が 0 の場合は等金額配分へフォールバックし警告ログを出力。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）を実装：既存ポジションを考慮して新規候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear に対応、未知値はフォールバック）。
    - 一部の設計上の注意（price が欠損時の挙動）をコメントとして記載。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック（risk_based / equal / score）を実装。単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に合わせたスケーリング）、cost_buffer による保守的見積りなどをサポート。
    - スケールダウン時の端数処理（lot 単位での再配分）を実装。

  - portfolio/__init__.py で主要関数をパッケージ公開。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを集約して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、コマンドラインで期間指定可能。

- データベース連携
  - run_* スクリプトやツールから sqlite3/duckdb を用いた接続処理を実装（Settings からパス取得）。
  - monitoring テーブル初期化を行う init_monitoring_db を起動時に呼び出すことで冪等に DB 構造を保証。

- 研究用モジュール（スケルトン）
  - research/factor_research.py
    - モメンタム等ファクター計算の骨組みを追加（DuckDB 接続を受け SQL + Python で計算する方針）。
    - 各種定数・計算対象窓（1M/3M/6M、MA200、ATR20 など）を定義。calc_momentum の実装開始（スケルトン）。

### Changed
- ログ出力の標準化
  - 全起動スクリプトで共通の setup_logging を最初に呼ぶ設計に統一。これによりログフォーマット・ローテーションが一貫化。

- DB パスの扱い
  - run_monitoring は環境にかかわらず本番用 sqlite_path を使う点を明示的に実装（監視の一貫性確保）。
  - run_execution は paper_trading の場合に paper_sqlite_path を使い本番 DB と分離する挙動を明確化。

### Fixed
- 環境変数パースの堅牢化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出し、デフォルトへフォールバックする挙動を実装（run_monitoring）。
  - .env 行パーサで export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを正しく処理。

- ログハンドラ二重登録回避
  - setup_logging は既存ハンドラを flush/close してから削除して再設定するようにし、重複出力を防止。

- プロセス優先度設定の失敗耐性
  - psutil の権限エラーや未実装ケース（AccessDenied / AttributeError / NotImplementedError）を捕捉し、警告のうえスキップするようにした。

- 停止フラグ／PID 管理の安全化
  - run_execution/run_monitoring で停止フラグの検知と安全停止処理（engine.stop() 等）を実装、既にフラグが立っている場合は起動せず終了する。

### Security
- 特別なセキュリティ修正はなし。
- 注意: .env ファイルは絶対にリポジトリにコミットしない旨の注記を config_setup に追加。

### Deprecated
- なし

### Removed
- なし

### Notes / TODO (既知の改善点・今後の作業)
- research/factor_research.py は計算ロジックの一部がスケルトンのまま（calc_momentum の続き等）。実データに対する検証・最適化が必要。
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合の過少見積問題に対するフォールバック価格（前日終値や取得原価など）を将来的に導入予定。
- position_sizing: 銘柄別の単元（lot_size）をマスタで管理する拡張（現在は全銘柄共通の lot_size 想定）が予定されている（TODO コメントあり）。
- ログディレクトリやファイルハンドラ作成に失敗したときの運用ドキュメント整備が必要。

---

このリリースは初期機能群（設定管理・起動スクリプト・ポートフォリオ構成ロジック・検証ツール・ユーティリティ）を提供し、自動売買システムの骨組みを構築することを目的としています。運用前に validate_config による設定検証と paper_trading による検証を強く推奨します。