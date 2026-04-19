# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。主なバージョンと機能追加・修正を日本語でまとめています。

※ この履歴は提供されたソースコードの内容から推測して作成した要約です。

## [Unreleased]

### Added
- モニタリング用スクリプト run_monitoring.py を追加
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止用フラグファイル（data/stop_requested.flag）を検知して安全にループ終了。
  - 監視コンポーネント（SystemMonitor）と監視 DB 初期化を統合。
- 実行エンジン起動スクリプト run_execution.py を追加
  - `KABUSYS_ENV=paper_trading` 時に専用のペーパートレード SQLite DB（data/paper_trading.db）を使用。
  - BrokerClientFactory によるブローカークライアント抽象化、ExecutionEngine の起動/停止制御（PID ファイル、停止フラグ）を実装。
- 設定管理モジュール config.py を実装
  - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を搭載。
  - `.env` / `.env.local` の読み込み順序、OS 環境変数保護（上書き防止）に対応。
  - 多数の設定プロパティを提供（DB パス、API トークン、環境種別、ログレベル、閾値等）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロード無効化可能。
- .env 作成/更新用の対話式ウィザード config_setup.py を追加
  - 対話式で .env を生成・更新し、保存前の確認とマスキング表示を行う。
  - デフォルト値や選択肢（KABUSYS_ENV 等）を提示。
- 設定検証 CLI validate_config.py を追加
  - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース検証（PyYAML が存在する場合）。
  - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギングユーティリティ utils/logging_setup.py を実装
  - ルートロガーに対して StreamHandler（stdout 出力）と TimedRotatingFileHandler（日次ローテーション）を設定。
  - LOG_DIR の自動作成処理と作成失敗時のフォールバック（コンソールのみ）を実装。
- プロセス優先度／CPU アフィニティ管理ユーティリティ utils/process_priority.py を実装
  - Windows / POSIX の差分を吸収して `set_process_priority`（high/normal/low）と `set_cpu_affinity` を提供。
  - psutil を利用し、権限不足などのケースでは警告ログを出してスキップ。
- ポートフォリオ構築関連モジュール（kabusys.portfolio）を実装
  - portfolio_builder: シグナル選定（select_candidates）、重み計算（calc_equal_weights, calc_score_weights）。スコア合計が 0 の場合は等配分にフォールバック。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数算出ロジック（risk_based / equal / score）、単元丸め、aggregate cap によるスケールダウン、cost_buffer 考慮。
- Paper Trading 検証レポート生成ツール tools/paper_verification_report.py を追加
  - システム安定性、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定を行う。
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` / CLI 引数で DB パスを指定可能。
- 研究用ファクター計算モジュール research/factor_research.py を追加（モメンタム等の計算ロジックを実装開始）
  - DuckDB を利用して prices_daily / raw_financials を参照する設計。モメンタム算出関数などを用意。

### Changed
- ロギングのデフォルト挙動
  - コンソール出力を stderr ではなく stdout に統一（cron やリダイレクトで扱いやすくするため）。
  - ハンドラ重複を防ぐため既存ハンドラをクリアして再設定。
- .env パーサを強化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い（クォートあり/なしの差分を考慮）。
  - OS 環境変数を保護するため既存のキーは上書きされない（必要に応じて .env.local で上書き可能）。
- 監視と実行プロセスの起動フロー
  - 起動時にプロセス優先度（"high"）を設定する呼び出しを追加。
  - monitoring は環境にかかわらず本番用 sqlite_path を明示的に使用する仕様に言及（run_monitoring の説明）。
  - execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と分離。

### Fixed
- .env 読み込みでのファイル読み取り失敗時に警告を出すように改善（例外回避）。
- ロギングハンドラ作成失敗時にアプリケーションを停止させないように修正（ファイルハンドラ作成に失敗したらコンソールのみで継続）。

### Notes
- 一部モジュール（research/factor_research.py）はファイル内容が途中で途切れているため（実装途中の可能性あり）、今後の完成が想定されます。
- config_setup が .env を生成する際に「.env は絶対に Git にコミットしないこと」を明記する等、運用上の注意喚起を含む出力を行います。

---

## [0.1.0] - 2026-04-19

初回公開。上記 Unreleased に記載の機能群を初期実装としてリリース。

### Added
- 基本的なアプリケーション構造とモジュール群を追加:
  - 実行/監視エントリポイント: run_execution.py, run_monitoring.py
  - 設定管理とウィザード: config.py, config_setup.py
  - 設定検証: validate_config.py
  - ロギング・プロセスユーティリティ: utils/logging_setup.py, utils/process_priority.py
  - ポートフォリオ構築関連: kabusys.portfolio パッケージ（builder, position_sizing, risk_adjustment）
  - Paper Trading 検証ツール: tools/paper_verification_report.py
  - 研究用ファクター計算開始: research/factor_research.py
- パッケージメタ情報:
  - バージョンを __version__ = "0.1.0" として設定。

### Changed
- 初期設計および実装に伴う各種デフォルト値と環境変数の定義を追加（例: DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, KABUSYS_ENV など）。

### Fixed
- 初期実装段階でのエラー処理とフォールバック（ログディレクトリ作成失敗時や psutil 権限エラー等）を追加して堅牢性を向上。

---

（今後のリリースでは各モジュールの完成、テスト、パフォーマンス改善、ドキュメント追記、research モジュールの完成等を反映予定です。）