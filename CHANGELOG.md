# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新のリリースは下に記載しています。将来の変更は Unreleased セクションに追記してください。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-24
初期リリース — KabuSys の基本機能を実装しました。主に自動売買エンジンの起動・監視周り、設定管理、ポートフォリオ構築・ポジションサイズ算出、検証ツールなどの基盤モジュールを含みます。

### Added
- 全般
  - パッケージ公開バージョンを追加（src/kabusys/__init__.py: `__version__ = "0.1.0"`）。
  - 豊富なドキュメンテーションコメントと型注釈を追加し、各モジュールの利用方法・設計方針を明記。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて paper_trading 用に専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組立、ExecutionEngine のスレッド実行、PID ファイル・停止フラグの扱いを実装。
    - RiskManager 用のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を導入。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して記録を一元化。
    - stop フラグ検知による安全停止、check_once() 実行時の例外ハンドリング、duckdb 接続の利用。

- 設定管理
  - config.py: Settings クラスを実装。
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で探索）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。
    - .env パースの堅牢化（export 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
    - 各種設定プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, CPU/メモリ/ディスク閾値、env/log_level 判定等）を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。
    - シークレットマスク表示、既存 .env の読み込み・再利用、書き込みテンプレート、保存確認フローを実装。

- 設定検証
  - validate_config.py: 起動前の環境検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日分）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順、ファイルハンドラ作成失敗時のフォールバック（コンソールのみ）を実装。
    - 既存ハンドラのクリアやフォーマット指定を行い二重設定を防止。
  - utils/process_priority.py:
    - psutil を使ったクロスプラットフォームのプロセス優先度設定（Windows / POSIX）および CPU affinity セット関数を提供。
    - 未対応 OS、権限不足時は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順かつタイブレークで signal_rank を使用して候補抽出。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限の判定と候補除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム(bull/neutral/bear) に応じた投下資金乗数（デフォルトフォールバックあり）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、lot_size による丸め、per-stock と aggregate の上限処理、cost_buffer を使った保守的見積り、スケールダウンと remainder による追加配分ロジックを実装。

- リサーチ
  - research/factor_research.py:
    - DuckDB を用いたファクター計算モジュールの骨格（モメンタム・MA200乖離、ATR、出来高系等）。関数インターフェースと定数を実装（calc_momentum の雛形を含む）。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite を読み込み、システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）などを計算して標準出力へ人間向けレポートを生成。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションで期間・DB を指定可能。

### Changed
- 設計上の仕様（初期化設計）
  - 監視用 DB（monitoring DB）について、init_monitoring_db() を呼び出して監視テーブルの存在を冪等的に保証するようにした。
  - ログは標準で stdout に出力する設計（cron やシェルリダイレクトとの親和性向上）。

### Fixed
- .env パーサの堅牢化
  - export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを改善し、.Linux / Windows の様々な .env 記述パターンへ対応。

### Security
- .env の取り扱いに関する注意喚起を config_setup.py に明記（.env を Git にコミットしない旨）。
- config.validate の live ガードで本番向け設定の未設定や危険値を警告するようにした。

### Notes / Non-functional
- 例外・権限不足・ファイル作成失敗時は fail-fast せずログ出力 / 警告を行い、可能な限り安全にフォールバックする設計を採用（logging/setup, process_priority, run_monitoring/exec の DB ハンドリング等）。
- 多くの関数は DB を直接変更しない純粋関数方式で設計されており、テスト容易性を考慮。

---

注: 本 CHANGELOG は提供されたソースコードの内容・コメントから推測して作成したものであり、実際の変更履歴・リリースノートと完全に一致するとは限りません。必要に応じて担当者で精査・編集してください。