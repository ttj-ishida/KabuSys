# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-22
初回リリース。本バージョンで導入された主な機能・改善点を列挙します。

### Added
- 基本パッケージ初期実装
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループを終了。
    - Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使用して DB を初期化。
    - duckdb への接続を確立し、監視用 DB 初期化ロジックを呼び出す。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いて実運用／モックブローカーを切り替え可能。
    - 実行中の PID ファイル管理、停止フラグ検知でエンジン停止の仕組みを実装。
    - デーモンスレッドで engine.run_session を起動し、定期的に停止フラグを監視して安全停止。

- 設定周り
  - config.py
    - Settings クラスを実装し、環境変数経由でアプリケーション設定を取得する共通 API を提供。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、PID ファイルやしきい値（CPU/MEM/DISK）やログレベル等をプロパティで取得可能。
    - PAPER_FILL_MODE に対するバリデーション（instant/partial/never/reject）を実装。
    - KABUSYS_ENV 値の正当性チェック（development/paper_trading/live）を実施。
    - 自動 .env 読み込み機能:
      - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を読み込み。
      - OS 環境変数を保護しつつ .env.local で上書きできる仕組みを提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

  - config_setup.py
    - 対話式ウィザードを提供し、.env の初期作成・更新を支援。
    - 各種設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH 等）を対話的に入力・確認して .env を生成。
    - シークレット項目はマスク表示、確認プロンプトを用意。

  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL/DB パスの検証、config/*.yaml の存在確認（PyYAML があればパース検査も実施）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
    - --strict オプションで警告も失敗扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ロギング初期化ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）を組み合わせて root ロガーを設定。
    - 既存ハンドラの重複設定を回避するため一度クリアしてから再設定。
    - LOG_DIR 環境変数や引数でログ出力先を指定可能。ファイル作成失敗時はコンソール出力にフォールバック。
    - ログレベル解決ロジック（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - 現在プロセスの優先度 (nice / Windows priority) をプラットフォーム依存を吸収して設定するユーティリティを追加。
    - set_cpu_affinity による CPU affinity 固定（最初 N コア）をサポート。
    - 権限不足や未サポート OS の場合は警告を出力して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 売買候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有比率が閾値を超えるセクターの新規候補を除外。
    - マーケットレジームに応じた乗数 calc_regime_multiplier を追加（bull/neutral/bear をサポート、未知値は警告の上フォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数を決定する calc_position_sizes を実装。
    - allocation_method（"risk_based"/"equal"/"score"）をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap、コストバッファを考慮したスケーリングロジックを実装。
    - 価格欠損時のスキップや、スケールダウン後の残余分配（端数処理）を丁寧に処理。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 向けの検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - 日付フィルタ（--from / --to）や DB パスの指定（--db / 環境変数）に対応。

- 研究用ファクター計算基盤
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。
    - モメンタム関連パラメータ（1M/3M/6M、MA200 等）の定義と calc_momentum の実装方針を記載（prices_daily を参照）。

- パッケージエクスポート
  - portfolio パッケージの __init__ で主要 API をエクスポート（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

### Changed
- なし（初回リリースのため変更履歴は無し）。

### Fixed
- なし（初回リリースのため修正履歴は無し）。

### Security
- なし（特記事項なし）。

---

注:
- .env のパース（config._parse_env_line）はシングル/ダブルクォートやエスケープ、行内コメント等に対応する堅牢な実装を意図しています。OS 環境変数は上書きを保護する設計になっています。
- 実際の運用・本番環境では KABUSYS_ENV の設定や KILL_FLAG_CLEAR_ON_START の値、LINE 通知設定などを慎重に確認してください（validate_config にてチェック可能）。
- 今後のリリースでは Reconciler / ExecutionEngine / SystemMonitor の詳細実装や research モジュールの完全実装、テスト追加、ドキュメント強化を予定しています。