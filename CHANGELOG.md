# CHANGELOG

すべての notable な変更は「Keep a Changelog」形式に準拠して記載しています。  
日付はリリース日です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止制御: プロジェクト data/stop_requested.flag を監視して安全にループ終了。
    - 監視用 DB は環境にかかわらず settings.sqlite_path（本番パス）を使用。
    - プロセス優先度を高 ("high") に設定してから起動。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag を監視し、検出時にエンジン停止処理を実行。
    - PID ファイルパス設定をサポート（data/execution.pid）。

- 設定管理・検証
  - config.py
    - .env の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）を実装。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、行内コメントに対応。
    - Settings クラスを導入し、各種設定（API トークン、DB パス、監視閾値、環境判定フラグ等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション、パスの Path 化、環境（development/paper_trading/live）検証を実装。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 各設定項目の説明、デフォルト、シークレット扱いをサポート。作成時に .env をファイルへ書き出す。
    - 既存 .env の読み込みと Enter による既存値再利用をサポート。

  - validate_config.py
    - 起動前に .env および config/*.yaml の不備を検出する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV・LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がある場合）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- portfolio モジュール（ポートフォリオ構築）
  - portfolio_builder.py
    - 候補選択 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) の純粋関数を追加。
    - スコアが全て 0 の場合は等金額配分にフォールバックし、警告を出力。

  - risk_adjustment.py
    - セクター集中制限を実施する apply_sector_cap を追加。既存保有のセクター暴露を計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear 対応、未知はフォールバック）。

  - position_sizing.py
    - 発注株数計算 calc_position_sizes を追加。
    - allocation_method に応じた計算（risk_based / equal / score）を実装。
    - lot_size 単位で丸め、per-position 上限、aggregate cap（利用可能現金超過時のスケーリング）、cost_buffer を考慮した安全な縮小ロジックを実装。

  - portfolio/__init__.py に公開 API をまとめてエクスポート。

- utils（ユーティリティ）
  - logging_setup.py
    - 共通ログ設定ユーティリティを追加。StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリーンアップを行い二重設定を防止。

  - process_priority.py
    - set_process_priority(level) を追加し、Windows と POSIX の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアにピン留め可能に（権限や未サポート OS では警告でスキップ）。

- tools
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）等を集計して判定 (PASS/FAIL) を出力。
    - CLI オプション --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
    - P95 計算、欠損データに対するフォールバックを実装。

- research
  - research/factor_research.py（ファクター計算モジュールの骨格を追加）
    - Momentum, Value, Volatility, Liquidity に関する設計方針・定数・calc_momentum の雛形を実装（DuckDB を用いた計算を想定）。
    - （実装途中の関数あり。将来的な拡張を想定。）

### Changed
- なし（初回リリースのためありません）。

### Fixed
- 設定パース/IO の堅牢化
  - .env の読み込み時、ファイル読み込み失敗で警告を出して処理を継続するよう実装（テストや権限問題に耐性）。
  - logging_setup でログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力のみで安全に継続するように修正。
  - run_monitoring のポーリング間隔取得で不正な値に対して警告し、デフォルト値にフォールバックするように修正（time.sleep に渡す不正値対策）。

### Notes / Developer-oriented
- 環境変数の自動読み込みはデフォルトで有効。テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading（KABUSYS_ENV=paper_trading）時は発注処理が MockBrokerClient を通じて行われ、データは別 DB（PAPER_TRADING_SQLITE_PATH）に保存され、本番 DB と分離されます。実運用時には KABUSYS_ENV を正しく設定してください（live は慎重に）。
- ログはデフォルトで logs/ ディレクトリに出力されます。権限や環境によってはファイル出力が失敗する可能性があるため、起動スクリプトは stdout にもログを出力します。
- process_priority/set_cpu_affinity は実行環境の権限に依存します。権限不足時は警告を出して処理をスキップします。
- research/factor_research.py は実装が途中の箇所があります（calc_momentum の実装開始）。本リリースではアルゴリズムの設計骨子と定数を提供しています。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

（本 CHANGELOG は公開されたソースコードから推測して記載しています。実装の背景や追加される予定の細部についてはレポジトリのコミット履歴やリリースノートを参照してください。）