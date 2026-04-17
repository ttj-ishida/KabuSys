# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
日付・バージョンはソース内の __version__ や実装内容から推測して記載しています。

## [Unreleased]

### Added
- 監視用ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検知で行う。
  - SystemMonitor を初期化し、SQLite / DuckDB に接続して定期チェックを行う。
  - 実行開始時にプロセス優先度を "high" に設定する。

- 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、paper_trading 用 SQLite（data/paper_trading.db など）へ記録することで本番 DB と分離。
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager の組み立てと起動。
  - 実行プロセスの PID ファイル管理（data/execution.pid）と停止フラグ検知によるグレースフルシャットダウン。
  - 実行開始時にプロセス優先度を "high" に設定する。

- 設定・環境変数読み込み機能を強化（src/kabusys/config.py）
  - プロジェクトルート（.git / pyproject.toml）を自動検出して .env を自動読み込み（.env → .env.local の順、OS 環境変数を保護）。
  - .env の行パースが強化：export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
  - 各種設定プロパティを提供（J-Quants, kabuAPI, DuckDB/SQLite パス、Paper Trading 設定、監視閾値、環境判定など）。
  - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 設定、KABUSYS_ENV / LOG_LEVEL の検証。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - .env と config/*.yaml の存在および基本整合性をチェックするツール。
  - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
  - PyYAML がインストールされていれば YAML のパース検証も実行。
  - --strict オプションで警告を FAIL 扱いにできる。

- .env 対話式ウィザードを追加（src/kabusys/config_setup.py）
  - 対話形式で .env の初期作成・更新を支援。シークレット項目はマスクして表示。
  - デフォルト値・選択肢・説明を備えた複数項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
  - 書き込みテンプレートに沿って .env を生成。

- ポートフォリオ構築モジュールを追加（src/kabusys/portfolio/*）
  - 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - 株数決定ロジック（calc_position_sizes）：risk_based / equal / score の割当方式、単元株（lot）丸め、最大ポジション上限・aggregate cap のスケーリング、cost_buffer を考慮した保守的見積。

- プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - Windows / POSIX (Linux/macOS/FreeBSD) の差を吸収してプロセス優先度を設定する set_process_priority(level)。
  - set_cpu_affinity(cpu_count) によるコア固定機能（未対応環境や権限不足時は警告でスキップ）。

- Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
  - paper_trading の SQLite DB から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。
  - CLI オプションで日付範囲（--from / --to）や DB パス（--db）を指定可能。
  - 判定基準（稼働率、成功率、送信率、P95 レイテンシ）を定義し PASS/FAIL 判定を行う。

- 研究用ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）
  - DuckDB の prices_daily テーブルを利用してモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、流動性指標等を計算する関数群を提供。
  - 空データや不足データに対する None ハンドリングや範囲バッファの考慮あり。

### Changed
- DB の取り扱い方針
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する（監視データは本番と共通で保存）。
  - 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全分離。

- 起動時のプロセス優先度設定を統一して常に最初に実行するように（run_monitoring / run_execution）。

### Fixed
- 環境変数の数値系設定（MONITOR_POLL_INTERVAL 等）に対する不正値検出とフォールバック処理を追加（負数やゼロは警告を出してデフォルトへフォールバック）。

### Documentation
- パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 と定義。
- 各スクリプト・モジュールに用途・使い方・注意点を示すドキュメンテーション文字列を追加。

---

## [0.1.0] - 2026-04-17

このバージョンは上記の機能群の初回実装に相当します。主な内容は以下の通りです。

### Added
- 初期リリース: 自動売買システムのコアユーティリティ群を実装。
  - 実行エンジン起動・監視ループ・停止フラグ管理。
  - 環境設定読み込み (.env 自動ロード)・対話式ウィザード・検証ツール。
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）。
  - Paper Trading 検証レポート生成ツール。
  - 研究用ファクター計算（モメンタム / ボラティリティ 等）。
  - プロセス優先度・CPU affinity ユーティリティ。

### Changed
- なし（初回リリースのため）。

### Fixed
- なし（初回リリースのため）。

---

注記:
- keep a changelog の慣例に従い、将来の変更は Unreleased セクションに追記してください。  
- 上記はコードベースから推測してまとめた CHANGELOG です。外部仕様や README などと差異がある場合は適宜調整してください。