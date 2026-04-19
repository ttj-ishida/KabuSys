CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
日付はリリース日を示します。

Unreleased
----------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------

初回公開リリース。

### Added
- 基本ランタイム・起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用エントリポイント。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、MockBrokerClient を利用可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルで安全停止を実装。
- 設定・環境周り
  - config.py: Settings クラスを導入。環境変数読み込み・検証ロジック（KABUSYS_ENV, LOG_LEVEL 等）を提供。プロジェクトルート自動検出（.git / pyproject.toml 基準）と .env/.env.local の自動読込に対応。
  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加（secret 入力、選択肢、保存確認など）。
  - validate_config.py: `.env` と config/*.yaml の事前検証 CLI（--strict オプションで警告を FAIL 扱いにできる）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing.py: 株数決定ロジック（risk_based / equal / score 対応）、単元株丸め、aggregate cap によるスケーリング、手数料/スリッページ考慮の cost_buffer。
  - portfolio パッケージ初期エクスポートを追加。
- 監視・実行の DB 初期化/統合
  - monitoring_db 初期化を実行時に行い、duckdb と sqlite の接続を提供（monitoring は環境にかかわらず本番 sqlite_path を使用、execution は paper_trading 時に専用 DB を使用）。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを提供。stdout に StreamHandler、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）を設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時のフォールバックあり。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティ。権限不足等の失敗時は警告を出して安全にスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を参照して稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）を集計・判定するレポート生成ツール。閾値に基づく PASS/FAIL 判定を出力。
- 研究用ファクター計算基盤（骨組み）
  - research/factor_research.py: DuckDB を使ったモメンタム等のファクター計算モジュールの雛形（API 設計、各ファクター算出方針・定数を定義）。

### Changed
- .env 自動ロードの方針
  - OS 環境変数を優先し、.env.local は .env の上書きとして扱う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- DB パスの扱い
  - 実行（execution）と監視（monitoring）で DB の利用ポリシーを明確化（paper_trading は分離された paper_sqlite_path を使用、監視は常に sqlite_path を利用して監視データを一元化）。
- ログ設定の堅牢化
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみで継続するフォールバックを実装。
- 環境変数パース改善
  - config._parse_env_line にて引用符つき値のエスケープ、行内コメントの扱い、export 形式のサポートなどを実装し、より実用的な .env パースを実現。

### Fixed
- 起動時の多重ログハンドラ追加問題を解消（既存ハンドラを flush/close してから削除し再設定）。
- process_priority / set_cpu_affinity は未対応 OS や権限不足により例外を投げないようにして安定性を向上。
- ポジションサイズ計算における合計投下額超過時のスケーリング処理で、端数（lot 単位）の再配分アルゴリズムを実装し、利用可能現金に合わせた割当ての再現性を改善。
- PAPER_FILL_MODE の検証（有効値チェック）を追加し、不正な値で起動することを防止。

### Security
- config_setup にて生成される .env ファイルのヘッダに「.env は絶対に Git にコミットしないこと」を明記。
- Settings._require により必須機密情報（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）が未設定の場合に明示的にエラーを出すようにして、秘密情報の欠落を早期検出。

### Notes / Usage
- 起動スクリプト:
  - 監視: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成。
  - 実行: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
- 設定ウィザード: python -m kabusys.config_setup（対話式で .env を生成）
- 設定検証: python -m kabusys.validate_config（--strict で警告を FAIL 扱い）
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力（30日保持）。LOG_DIR 環境変数で変更可能。

今後の予定（例）
- research/factor_research のファクター計算実装完了（SQL/分析ロジックの充実）。
- テストカバレッジの拡充（特に position sizing のスケーリング、リスク制御周り）。
- 銘柄別の単元株数対応（lot_size を銘柄別設定に拡張）。