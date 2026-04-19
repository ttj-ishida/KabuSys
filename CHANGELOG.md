# Changelog

すべての重要な変更をこのファイルに記録します。  
形式は Keep a Changelog に準拠します。  

現在の日付: 2026-04-19

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。KabuSys 自動売買フレームワークの基盤機能を収録しています。

### Added
- 実行エントリ / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag を監視して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル（data/execution.pid）を指定可能。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - POLL 間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60秒、負値/0 はデフォルトにフォールバックして警告出力）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループ停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: Settings クラスを実装。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - キーの必須チェック（_require）、各種パスのプロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）、環境 (KABUSYS_ENV) 検証、paper_fill_mode 検証、各種閾値の取得。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の初期作成 / 更新）。
    - 秘匿入力対応、既存 .env の読み込み、書式化された .env 保存。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML がない場合は警告）。
    - --strict オプションで警告をエラー扱いに可能。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログ保持 (backupCount) は 30 日。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity のユーティリティを追加。
    - Windows/Linux(Mac含むPOSIX) に対する抽象化、例外発生時は警告出力してスキップ。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート・上位 N 抽出（スコア降順、同点は signal_rank 小さい方優先）。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用して候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数決定（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合はスケーリングと端数分配アルゴリズム）を実装。
    - cost_buffer による保守的コスト見積り対応。
  - package export: kabusys.portfolio パッケージとして主要関数をエクスポート。

- 研究・分析
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム・移動平均乖離・ATR 等を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - （本スナップショットでは calc_momentum の実装が途中である箇所あり）

- ツール類
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 引数で期間指定 (--from / --to) と DB パス指定 (--db) をサポート。環境変数 PAPER_TRADING_SQLITE_PATH にも対応。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどを集計し PASS/FAIL 判定（デフォルト閾値をコード内で定義）。
    - P95 計算、Null/データ欠損の扱い、エラー時のフォールバックを実装。

- パッケージ情報
  - __init__.py にてパッケージ名とバージョンを定義（__version__ = "0.1.0"）および主要サブパッケージを __all__ で公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （本リリースでは特記なし）

---

備考:
- 環境変数や .env の取り扱いはセンシティブな情報（API トークン等）を含むため、.env を絶対にリポジトリにコミットしない旨の注意が config_setup.py に記載されています。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する設計になっています。paper_trading 環境での監視データ分離が必要な場合は設定・設計の見直しを検討してください。
- research/factor_research.py は設計方針が記載されており、DuckDB によるファクター計算を前提としていますが、実装の続き（complete な関数群）は今後の追加対象です。