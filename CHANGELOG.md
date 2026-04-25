# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
リリースバージョンはパッケージ内の __version__ に合わせて 0.1.0 としています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-25

初期リリース。日本株自動売買システム「KabuSys」のコア機能とユーティリティを追加しました。

### Added
- パッケージ初期導入
  - パッケージ名: kabusys、バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring などのサブパッケージ構成

- 実行エントリ / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を検知して安全に終了。
    - 監視用 DB は KABUSYS_ENV に依らず本番 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用したブローカークライアントの抽象化。
    - 停止フラグ・PID ファイル管理（data/execution.pid, data/stop_requested.flag）に対応。

- 設定管理
  - config.py
    - Settings クラスで環境変数を集中管理。
    - 自動的にプロジェクトルートの .env / .env.local を読み込み（無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
    - PAPER_FILL_MODE の入力検証（有効値: instant/partial/never/reject）。
    - 各種パス設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や監視閾値のプロパティを提供。

- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目のマスク表示、既存値の読み込み・再利用、確認後にファイル保存。
  - validate_config.py
    - .env と config/*.yaml の事前バリデーション CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がインストールされていない場合は警告）などを行う。
    - --strict モードで警告を FAIL 扱いにできる。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL を判定する閾値を定義（例: 稼働率 >= 99% 等）。
    - CLI オプションで期間指定（--from / --to）や DB パス指定（--db）が可能。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（既存保有を考慮し、max_sector_pct を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知のレジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元株丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り。
    - スケールダウン時の残差処理（lot 単位での追加配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの初期化ユーティリティ。
    - stdout に出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler・30日保持）のファイルハンドラを設定。
    - ログディレクトリの自動作成と、作成失敗時にはファイル出力をスキップして stdout のみで継続する。ログレベルは引数 > 環境変数 > デフォルト の順で解決。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティ。
    - Windows（psutil の priority class）と POSIX（nice 値）に対応。アクセス拒否など失敗時は警告を出してスキップ。
    - set_cpu_affinity による CPU ピニング機能（オプション）。

- データベース接続
  - duckdb を分析用に利用（duckdb_path プロパティ）。
  - sqlite3 を監視・注文履歴・ペーパートレード記録に使用。

- 研究用モジュール（骨格）
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials を用いたファクター計算関数群の実装方針と初期定数を追加（モメンタム・MA・ATR 等）。実装は一部（ファイル末尾で未完）あり。

### Changed
- ロギング
  - 標準出力を stdout に統一している（StreamHandler を stdout に設定）。
  - 日次ローテーション・ファイルハンドラを追加し、ログディレクトリ作成失敗時は console のみでフォールバックする挙動に変更。
- 環境変数読み込みの挙動
  - .env.local は .env の後に上書き（override=True）。既存の OS 環境変数は保護（protected）して上書きされない。

### Fixed
- run_monitoring のポーリング間隔取得ロジックで、MONITOR_POLL_INTERVAL が 0 以下や不正な値の場合にデフォルト値へフォールバックするように修正（ValueError 発生を回避）。
- .env ファイル読み込みでファイルオープンに失敗した場合の警告出力（warnings.warn）を追加し、読み込み失敗時にもプロセスが継続するように改善。
- process_priority / set_cpu_affinity の失敗時に発生しうる例外（AccessDenied 等）をキャッチして警告を出し、処理を継続するように改善。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - 価格が欠損（0.0）の場合にエクスポージャーが過少評価される旨の注釈あり。将来的に前日終値や取得原価等のフォールバックを検討。
- portfolio/position_sizing:
  - 現状単元株数 (lot_size) は全銘柄共通。将来的に銘柄毎の lot_size を受け取る設計拡張を検討中（TODO コメントあり）。
- research/factor_research.py は骨格・定数定義と docstring が中心で、一部実装が未完（ファイル末尾が切れている）。実装の続きが必要。

### Breaking Changes
- なし（初期リリースのため互換性問題なし）。

---

もしリリース日や追加のマイナー修正を反映したい場合は、リリース日や該当変更を教えてください。必要に応じて英語版や追加のセクション（セキュリティ、マイグレーション手順等）も作成します。