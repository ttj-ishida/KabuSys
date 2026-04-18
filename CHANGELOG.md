# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

現在のリリースバージョンは __0.1.0__ です。

## [Unreleased]
（現時点のコードスナップショットに基づく初期リリースの記録を以下に示します）

## [0.1.0] - 2026-04-18

### Added
- 基本的な日本株自動売買フレームワークを初期実装。
  - パッケージ名: `kabusys`、バージョン `0.1.0` をパッケージメタデータに追加。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。スレッドでエンジンを実行し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔オーバーライド、停止フラグ検知、例外のログ出力を実装。
- Paper trading サポート
  - KABUSYS_ENV により `paper_trading` モードを判定。ペーパートレード時は MockBrokerClient（ファクトリ経由）を使用し、本番 DB と分離された `data/paper_trading.db` を既定として使用。
- 設定管理
  - `kabusys.config.Settings`：環境変数からの設定読み取りを統一化。多数の設定プロパティ（DB パス、API トークン、監視しきい値、ログレベル等）を提供。
  - 自動 .env ロード機能：プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み（OS 環境変数を保護）、テスト時に自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `.env` のパースはクォートやエスケープ、インラインコメントに対処する堅牢な実装を提供。
- 設定支援ツール
  - `kabusys.config_setup`：対話式ウィザードで .env を初期作成・更新する CLI を提供。シークレット値はマスク表示し、保存前に確認を促す。
  - `kabusys.validate_config`：起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が利用可能な場合）などをチェックし、警告／エラーを報告。`--strict` で警告も失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：StreamHandler（stdout）と TimedRotatingFileHandler（ファイル、日次ローテーション・30日保持）をルートロガーに設定。ログディレクトリの作成を試み、失敗時はコンソール出力のみで継続。
  - `kabusys.utils.process_priority`：Windows / POSIX を吸収したプロセス優先度（high/normal/low）設定、CPU affinity 設定を提供。権限不足等で失敗しても警告でスキップする堅牢な実装。
- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - select_candidates: スコア降順で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重で重みを計算（スコアが全て 0 の場合は等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap: セクター集中を検査して候補を除外する機能（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告を出して 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes: 等分配・スコア基準・リスクベースの各方式に対応した株数計算。単元（lot_size）で丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュに基づく端数補正ロジックを実装。
  - これらをまとめて `kabusys.portfolio` パッケージとして公開。
- 解析・研究用モジュール
  - `kabusys.research.factor_research`：DuckDB 接続を受けてモメンタムなどのファクターを計算する骨格を追加（モメンタム計算関数など）。設計は prices_daily / raw_financials テーブル参照、Zスコア正規化との連携を想定。
- ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading の検証レポート生成 CLI を追加。指定期間の稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）やリスク却下数を集計し、定義された閾値に基づいて PASS/FAIL を判定する。既定閾値:
    - 稼働率: 99.0%
    - 注文成功率 (fill_rate): 90.0%
    - 送信率 (send_rate): 95.0%
    - P95 レイテンシ: 200 ms

### Changed
- ログ出力: コンソールは stdout を使用するように明示（cron 等で stdout/stderr を統合して扱いやすくするため）。
- run_monitoring は KABUSYS_ENV にかかわらず監視用 DB（sqlite_path）として本番設定の sqlite_path を使用する仕様を明記（監視データは環境に依存しない本番の監視対象として扱う想定）。
- run_execution は paper_trading モード時に専用 SQLite（paper_sqlite_path）を使用し本番 DB と完全分離する動作を採用。

### Fixed
- run_monitoring のポーリング間隔取得処理で、不正な MONITOR_POLL_INTERVAL 値に対してデフォルト（60秒）にフォールバックし、ログで警告を出すように修正（time.sleep に負の値を渡すことによる ValueError を回避）。
- .env パーサでのクォート付き値やバックスラッシュエスケープ、コメントの取り扱いを強化。export プレフィックスにも対応し、より実運用での .env の多様な書き方を許容。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップして安全に続行するよう改善、事前に既存ハンドラを flush/close して重複設定を防止。

### Security
- config_setup の対話表示ではシークレット項目（J-Quants / kabu API パスワード 等）をマスク表示して、誤って端末に露出しないよう配慮。
- Settings._require を用いて必須環境変数が未設定の場合は明示的に例外を投げ、起動前に安全性の担保を行う。

### Notes / Operational hints
- process_priority の適用は最良努力 (best-effort) の設計：権限不足、未サポート OS では警告を出してスキップするため、必ずしも優先度が変わるとは限らない点に注意。
- 本番環境での Kill Switch（KILL_FLAG_CLEAR_ON_START）はデフォルト "0" を推奨。`validate_config` では KABUSYS_ENV=live 時の設定ミス（LINE 通知未設定、Kill フラグ自動クリアの危険設定）を警告するガードを備える。
- position_sizing や apply_sector_cap では価格の欠損（0.0）がある場合の影響がコメントで指摘されており、将来的にフォールバック価格導入が検討されている。
- DuckDB は分析用に統合されており、Execution / Monitoring から接続して利用する想定（設定で DUCKDB_PATH 指定可）。

### Removed
- （今回の初期リリースにおける削除項目はありません）

---

今後の改善候補（未実装／検討中）
- 銘柄別の lot_size をサポートするためのマスタ導入（position_sizing の TODO）。
- price が欠損する場合のフォールバック価格ロジック（前日終値 / 取得原価など）。
- factor_research の各ファクター実装完了および単体テスト整備。
- 実行エンジン（ExecutionEngine）や SystemMonitor の詳細実装に対する E2E テスト、モックを用いた自動化。