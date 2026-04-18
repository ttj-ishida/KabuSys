# Changelog

すべての重要な変更を Keep a Changelog の形式で日本語で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回リリース — KabuSys 自動売買システムの基盤機能を追加。

### Added
- コア実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）を利用して本番 DB と完全分離。
    - 停止フラグファイル (data/stop_requested.flag) および実行用 PID ファイル (data/execution.pid) のサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトへフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を明示。

- 設定・環境管理
  - config.py: Settings クラスを追加
    - 環境変数から設定を取得するプロパティ群を提供（DB パス、API トークン、ログレベル、監視閾値、環境判定など）。
    - `.env` 自動ロード機能（プロジェクトルートが検出できる場合に .env および .env.local を読み込む）。OS 環境変数は保護される（上書き回避）。
    - `.env` パースロジックで `export KEY=val`、クォートやエスケープ、インラインコメントなどに対応。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードの無効化が可能。
    - `paper_fill_mode` の検証（有効値: "instant"|"partial"|"never"|"reject"）や Paper Trading 用 SQLite パスプロパティを追加。

  - config_setup.py: 対話式 .env 作成ウィザードを追加
    - 主要な環境変数を対話的に作成・更新する CLI。
    - 秘密項目はマスク表示、保存前の確認と .env ファイル書き込みを提供。

  - validate_config.py: 設定検証 CLI を追加
    - 必須/任意環境変数、KABUSYS_ENV、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAML がある場合）などを検証。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境 (KABUSYS_ENV=live) に対するガード（LINE 通知設定や Kill Switch 設定の警告）を追加。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - stdout を用いることでスケジューラ実行時のリダイレクトを容易に。

  - utils/process_priority.py: プロセス優先度・CPU affinity ユーティリティを追加
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収した優先度設定 (`set_process_priority`)。
    - `set_cpu_affinity` で最初の N コアに固定可能（アクセス権限エラー等は警告でスキップ）。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコアでソートして上位 N 件を返却。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算（全スコア 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知はフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき発注株数を計算。
    - lot_size 単位での丸め、1 銘柄上限・aggregate cap（available_cash に合わせたスケーリング）を実装。
    - cost_buffer を用いた保守的なコスト見積もりと残差配分ロジックを実装。
    - 多数のパラメータで挙動を調整可能（risk_pct, stop_loss_pct, max_position_pct, max_utilization, etc.）。

- DuckDB / SQLite の統合
  - DuckDB 接続を使用する設計（分析用 DB: DUCKDB_PATH）。
  - 監視・イベント保存用に SQLite を使用（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを算出。
    - 既定の合格閾値を設定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - 日付フィルタ、DB パス指定オプションをサポート。

- リサーチ用ファクター計算（骨格）
  - research/factor_research.py: momentum 等のファクター計算モジュールの基礎実装を追加（DuckDB の prices_daily を参照して複数期間のリターンや MA200 乖離を計算する設計）。（注: ファイル末尾が部分的に実装/未完）

- パッケージ初期化
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。公開 API を __all__ で明示。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし

### Notes / Known issues / TODO
- research/factor_research.py が途中で未完の実装となっている（ファイル末尾で切れているため実装続行が必要）。
- position_sizing.py 内に「price が欠損（0.0）の場合のフォールバック処理」や、将来的な lot_size の銘柄別対応などの TODO コメントあり。
- apply_sector_cap は "unknown" セクターを保護しているが、データ欠損時のエクスポージャー過少見積りについて注意喚起あり。
- .env パーサは多くのケースに対応しているが、特殊なエスケープや複雑なフォーマットは手動確認推奨。

---

このリリースはシステムの基盤機能（設定管理、起動スクリプト、監視・実行エンジンの連携、ポートフォリオ構築ロジック、Paper Trading 検証ツール、ログ・プロセス管理ユーティリティ）を提供します。以降のリリースでは research モジュールの完成、テスト追加、運用上の微調整（フォールバック戦略、エラーハンドリングの強化等）を予定しています。