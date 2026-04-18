# Changelog

すべての注目すべき変更をここに記録します。  
このリポジトリはセマンティックバージョニングに従います。  

フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初回公開リリース。パッケージメタ情報を `src/kabusys/__init__.py` にて v0.1.0 として設定。
  - DuckDB と SQLite を組み合わせたデータ基盤統合（設定によりパス指定可能）。
- 起動スクリプト / 実行系
  - 実行エンジン起動スクリプトを追加（`src/kabusys/run_execution.py`）。
    - KABUSYS_ENV が `paper_trading` の場合は paper trading 用 DB（`data/paper_trading.db` をデフォルト）を利用し、Mock ブローカーを想定した分離を実現。
    - プロセス優先度を最初に `high` に設定する仕組みを導入（`utils.process_priority.set_process_priority` を使用）。
    - PID ファイル（`data/execution.pid` デフォルト）と停止フラグ（`data/stop_requested.flag`）による起動／停止制御。
    - ExecutionEngine を別スレッドで起動し、メインループで停止フラグを監視して安全に停止。
- 監視系
  - システム監視ポーリングループ起動スクリプトを追加（`src/kabusys/run_monitoring.py`）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（既定 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - 停止フラグファイルによるループ終了と例外時のログ出力を備える。
- 設定管理・ウィザード・検証
  - 環境設定管理モジュールを追加（`src/kabusys/config.py`）。
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env のパースは export 形式・クォート・コメントに対応する頑健な実装。
    - Settings クラスで環境変数（DB パス、API トークン、運用モード、しきい値など）を集中管理。値の検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
  - 対話式 .env 作成・更新ウィザードを追加（`src/kabusys/config_setup.py`）。
    - 主要な環境項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB/SQLITE パス等）に対応。
    - 既存 .env の読み取りと Enter による既存値再利用、保存前の確認プロンプトを提供。
  - 設定検証 CLI を追加（`src/kabusys/validate_config.py`）。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - `--strict` オプションで警告をエラー扱いにするモード。
    - 本番（live）用のガード（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START 設定など）による注意喚起。
- ポートフォリオ構築（純粋関数、DB 参照なし）
  - 候補選定・重み計算（`src/kabusys/portfolio/portfolio_builder.py`）
    - シグナルのスコア順ソート（タイブレークに signal_rank を使用）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（`src/kabusys/portfolio/risk_adjustment.py`）
    - セクター上限（max_sector_pct）に基づく候補除外ロジック。`unknown` セクターは制限対象外。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知のレジームはログ警告とフォールバック）。
  - 株数決定・投下資金調整（`src/kabusys/portfolio/position_sizing.py`）
    - risk_based / equal / score の割当方式をサポート。単元株（lot_size）で丸め、per-position 上限・aggregate cap を考慮してスケールダウン。
    - cost_buffer による保守的見積りをサポート。残余キャッシュに基づく再配分ロジックを実装。
  - 上記モジュールをまとめてエクスポートするパッケージ API（`src/kabusys/portfolio/__init__.py`）。
- ユーティリティ
  - ロギング設定ユーティリティを追加（`src/kabusys/utils/logging_setup.py`）。
    - コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに一括設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 環境変数 LOG_LEVEL / LOG_DIR による設定、アプリ名ごとのログファイル名対応。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（`src/kabusys/utils/process_priority.py`）。
    - Windows と POSIX（Linux/Mac 等）に対応した優先度設定（nice / HIGH_PRIORITY_CLASS 等を利用）。失敗時は警告ログを吐いてスキップ。
    - CPU affinity 固定機能（最初の N コアに固定）を実装。
- paper trading / 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（`src/kabusys/tools/paper_verification_report.py`）。
    - system_status / trade_logs / risk_logs を参照し、稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計して PASS/FAIL 判定を出力。
    - CLI 引数で期間指定（--from, --to）と DB パス指定（--db）をサポート。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（未指定時 data/paper_trading.db）。
- リサーチ
  - ファクター計算（`src/kabusys/research/factor_research.py`）の枠組みを追加。
    - モメンタム / Value / Volatility / Liquidity などを計画。DuckDB の prices_daily / raw_financials を参照する設計で、日数定数や計算方針を定義。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Known limitations / Notes
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップする（配布後の動作を考慮）。
- `position_sizing.calc_position_sizes` の価格欠損時の挙動に注意（ソース内に将来的な価格フォールバックの TODO コメントあり）。
- リサーチモジュール（factor_research）は機能設計が含まれているが、実装の一部が継続開発を想定している可能性がある（本リリースでは枠組み中心）。
- ログディレクトリ作成やプロセス優先度設定は環境によっては権限エラーでスキップされる（警告ログを出力）。

### Security
- （初版のため該当なし）

---

参考: 主要な環境変数
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading のフィルモード: instant/partial/never/reject）

もし追加で過去のリリース履歴や細かい変更点（コミット単位の記述）を希望される場合は、コミットログや差分を提供してください。