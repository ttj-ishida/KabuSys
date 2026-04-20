# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。  
リリースはセマンティックバージョニングに従います。

※ 本 CHANGELOG はコードベース（src/ 以下）の内容から機能・振る舞いを推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-20
最初の公開リリース。本リポジトリのコア機能（実行/監視ランナー、設定管理、ポートフォリオ構築、ユーティリティ、検証ツール等）を実装。

### Added
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に応じて paper_trading の場合は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知による安全な終了処理を実装。
    - 実行中の PID を data/execution.pid に管理（pid_file 機能を利用）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ検知でループ終了、KeyboardInterrupt による終了処理を実装。

- 設定管理
  - config.py: 環境変数と .env 自動読み込み機能を実装。  
    - プロジェクトルートを .git / pyproject.toml から検出して .env/.env.local を自動読み込み（OS 環境変数は保護）。
    - export KEY=val 形式やクォート、インラインコメント等に対応した堅牢な .env パーサを提供。
    - 各種設定プロパティ（DB パス、LINE トークン、監視閾値、KABUSYS_ENV 判定、paper_trading 用オプション等）をラップする Settings クラスを提供。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - KILL_FLAG_CLEAR_ON_START など運用系フラグをサポート。

- 設定ウィザード & 検証 CLI
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。  
    - 既存 .env の読み込み、シークレット値のマスク表示、保存確認機能を提供。
  - validate_config.py: 起動前チェック CLI を追加。  
    - 必須/任意環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証を実施。
    - --strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（pure function）
  - portfolio/portfolio_builder.py: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
    - apply_sector_cap は sell_codes（当日売却予定）を考慮して既存ポジションからのエクスポージャーを計算。unknown セクターは制限対象外。
    - calc_regime_multiplier は既知レジームに対する乗数を返し、未知値は 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）。  
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - lot_size（単元株）に合わせた丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケーリングを実装。
    - 価格欠落時のスキップとログ出力、スケーリング時の残差処理（lot 単位で追加配分）を実装。

- 研究・ファクター計算（骨格）
  - research/factor_research.py: Momentum 等のファクター計算モジュールを追加。  
    - DuckDB 接続を受け取り prices_daily / raw_financials を基に計算する設計（関数インターフェースと定数群を定義）。※ 実装は続きあり（ファイル末尾で途切れています）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。  
    - SQLite（デフォルト: data/paper_trading.db）からシステム安定性（稼働率）、注文成功率、送信率、レイテンシ、リスク却下数等を集計してレポート出力。
    - デフォルト判定基準（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - コマンドラインで期間指定（--from/--to）や DB パス指定（--db）に対応。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - console (stdout) と TimedRotatingFileHandler（日次・30世代保持）をルートロガーへ設定。
    - 既存ハンドラをクリアして二重登録を防止、ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。  
    - Windows 用定数と POSIX の nice 値を扱い、対応外 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity により最初の N コアにピンニング可能（存在しない場合は全コア使用）。

- パッケージメタ
  - パッケージ初期化 (__init__.py) にバージョン 0.1.0 を設定。

### Changed
- 初期リリースのため変更履歴はありません（最初の導入）。

### Fixed
- 初期リリースのため修正履歴はありません（最初の導入）。

### Notes / 備考
- .env の自動読み込みは、テストや特殊な実行環境で無効化できる: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- monitoring 用 DB 初期化関数 init_monitoring_db が run_execution/run_monitoring の両方から冪等に呼ばれており、監視テーブルの存在を保証。
- 一部モジュール（research/factor_research.py 等）は大枠の実装や定数定義まで完了しているが、ファイル末尾が途切れている箇所があり追加実装が必要な可能性があります。

---

（参考）今後の更新で記載すべき項目の例:
- ExecutionEngine / SystemMonitor の詳細な動作改善やエラーハンドリングの追加
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の集計）
- ユニットテスト追加、CI 設定、ドキュメント強化、運用ランブックの追加

もしこの CHANGELOG に追加したい変更点やリリース日付の修正、より細かい分類（Fixed/Deprecated 等）があれば指示してください。