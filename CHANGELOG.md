# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。  
このファイルはコードベースから実装内容を推測して作成しています。

全般的なルール:
- 重要な追加機能、改善、修正をカテゴリ別に列挙しています。
- 日付はこの CHANGELOG 作成日 (2026-04-20) を用いています。

## [0.1.0] - 2026-04-20

### Added（追加）
- 実行スクリプト
  - run_execution.py を追加。ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine のセッション実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) によるプロセス制御。
- 監視スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグ検知でループを安全に終了。
- 設定管理
  - config.py を追加。Settings クラスで環境変数をラップして提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等のパス解決を Path オブジェクトで提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証、各種しきい値（CPU/MEM/DISK）や kill flag 設定の取得。
    - 自動で .env / .env.local ファイルをプロジェクトルートから読み込む機能（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化あり）。
- .env ウィザードと検証
  - config_setup.py を追加。対話式ウィザードで .env を作成・更新するユーティリティ。
    - シークレット入力の扱い、既存 .env 読み込み、確認プロンプト、ファイル書き出し機能を提供。
  - validate_config.py を追加。起動前に環境変数や config/*.yaml の有無・基本的な妥当性をチェックする CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース可否チェック（PyYAML 未インストール時はスキップ）、本番環境向けの追加ガードを実装。
    - --strict モードで警告を FAIL 扱いにできる。
- ロギング周り
  - utils/logging_setup.py を追加。全アプリから利用できる統一ロギング設定を提供。
    - stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせた設定。
    - LOG_DIR / LOG_LEVEL の解決ロジック、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度ユーティリティ
  - utils/process_priority.py を追加。Windows/Linux/macOS を吸収するプロセス優先度（nice / Windows priority class）設定と CPU affinity 設定を提供。
    - psutil による実装で、実行不可時には警告を出して安全にスキップする。
- ポートフォリオ構築ライブラリ
  - portfolio/package を追加:
    - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - risk_adjustment.py: セクター集中上限適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装。
    - position_sizing.py: position size 計算 (calc_position_sizes)。risk_based / equal / score の配分方式、単元株化（lot_size）、aggregate cap によるスケールダウンロジック、コストバッファ考慮などを実装。
    - portfolio パッケージ __init__.py で主要関数をエクスポート。
- DuckDB 統合
  - run_* スクリプトや research モジュールから duckdb.connect を使用して分析用 DB を扱う実装を導入。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。ペーパートレード用 SQLite を読み、システム稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計してレポート出力。
    - 各種閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションを持つ CLI。
- リサーチ基盤（開始）
  - research/factor_research.py を追加（断片）。DuckDB から株価・財務データを参照してモメンタム等のファクター計算を行う設計を導入（モジュールは未完の箇所あり）。
- パッケージ情報
  - kabusys/__init__.py に __version__ = "0.1.0" を追加（初期リリース番号）。

### Changed（変更・仕様）
- run_monitoring と run_execution の起動時に最初にプロセス優先度を "high" に設定する仕様を導入。
- logging_setup は stdout を標準出力に使用する方針を明示（cron/Task Scheduler のリダイレクトを考慮）。
- .env 自動読み込みの優先順位を OS 環境変数 > .env.local > .env とし、OS 環境変数は保護（上書き禁止）する仕様を実装。
- .env パーサーの強化:
  - export KEY=val 形式をサポート
  - シングル/ダブルクォート内でのバックスラッシュエスケープを処理
  - コメント処理（クォート外の '#' を場合に応じてコメントとみなす）
- Settings による環境変数検証を強化（値の妥当性チェックやデフォルト値提供）。
- position_sizing のスケーリングロジックに cost_buffer を導入し、手数料・スリッページを保守的に見積もる挙動を追加。

### Fixed（修正）
- run_execution/run_monitoring 共通:
  - 停止フラグ存在時に安全に起動を回避または動作を停止するハンドリングを追加（既存停止フラグ検知による早期終了対応）。
- logging_setup:
  - ハンドラがすでに存在する場合に一度 flush/close してから再設定することで二重ログ出力を防止。

### Notes（備考）
- validate_config の YAML 検証は PyYAML がインストールされていない場合はスキップされる（警告のみ）。
- research/factor_research.py はモジュール設計・定数や calc_momentum の関数シグネチャを含むが、実装の一部が未完（ファイル末尾で途中）であるため、将来的な追加実装が想定される。
- process_priority と set_cpu_affinity は psutil に依存しており、環境によってはアクセス権限やプラットフォームの違いで機能が限定されることがある（警告を出して安全に継続する実装）。

---

初期リリース (0.1.0) はシステムのコア（実行/監視/設定管理/ポートフォリオ構築/検証ツール/ログ設定/プロセス制御）を一通り揃えたものです。今後、research モジュールの完成、テストケース追加、エラーハンドリングや Observability の強化（メトリクス・アラート連携）などが想定されます。