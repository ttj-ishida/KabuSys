# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-25

### Added
- 全体
  - 初期リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール等を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用して接続。
    - stop_requested.flag により安全にループを終了可能。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db にデータを記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。停止フラグの検出で実行中エンジンを安全に停止。
    - 実行用 PID を data/execution.pid に記録する仕組み（pid_file パスの受け渡し）。

- 設定管理 / 検証 / ウィザード
  - config.py
    - .env/.env.local の自動読み込み機構を実装（プロジェクトルートの検出: .git または pyproject.toml ベース）。
    - .env の行パースロジックを強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスを導入し、各種環境変数（DB パス、API トークン、Paper Trading の設定、監視閾値など）を型化・検証付きで提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みの無効化が可能。
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。多くの設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定等）を対話的に編集・保存可能。
    - 既存 .env の読み込み・マスク表示・確認フローを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリチェック、YAML のパースチェック（PyYAML があれば実施）、本番環境時の追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。

- utilities
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを提供。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - 既存ハンドラの二重登録防止、ログディレクトリ自動作成、作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収する実装。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存ポジションと価格情報からセクター別エクスポージャを算出して候補をフィルタ。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based"、"equal"、"score"）に対応した株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金を超える場合はスケーリング）、cost_buffer を考慮した保守的見積り、端数配分ルール（残差に基づき lot 単位で追加配分）を実装。

- 監視・検証ツール
  - monitoring.monitoring_db の初期化利用（各起動スクリプトから呼び出し、監視テーブルの存在を保証）。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定する。
    - P95 計算、期間フィルタ、DB パス解決（--db / 環境変数 / デフォルト）をサポート。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を採用。

- リサーチ
  - research/factor_research.py（骨子を追加）
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を行うモジュールの雛形を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - モメンタム計算（1M/3M/6M、MA200 乖離）等の定義と定数が追加（実装は一部ファイル末尾で未完）。

### Changed
- 起動・DB ポリシー
  - 監視プロセスは KABUSYS_ENV に依存せず常に本番用 sqlite_path（デフォルト data/monitoring.db）で監視テーブルに接続するよう明確化。
  - 実行（execution）は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 DB と分離する挙動を明示。

- .env 読み込みの優先度
  - OS 環境変数 > .env.local > .env の順で読み込む。既存 OS 環境変数は保護され、.env.local は上書き可能。

- ロギング
  - setup_logging により既存ハンドラを一旦閉じてから再設定するため、複数回呼ばれても二重にログが出力されないように変更。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサがクォート内のバックスラッシュエスケープやインラインコメントを正しく扱うよう改善。不正行は無視され、export プレフィックスにも対応。

- プロセス優先度の例外ハンドリング
  - 権限不足や未サポート環境での失敗をキャッチし、アプリケーションを停止させずに警告ログを出すように修正。

- position_sizing のスケーリング端数処理
  - aggregate cap によるスケーリング後の残余キャッシュを使って lot_size 単位で再配分するアルゴリズムを導入。再現性のため同値時の整列順序を安定化。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注:
- research/factor_research.py はファイル末尾が途中で切れている（実装途中）ため、当面は実験的な位置づけです。
- このリリースの各 CLI（python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）は運用前に .env を適切に設定・検証することを推奨します。