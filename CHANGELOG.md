# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
バージョン番号はパッケージの src/kabusys/__init__.py の __version__ に合わせています。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成を実装（初期リリース）
  - パッケージ概要: kabusys — 日本株自動売買システム（src/kabusys/__init__.py）
- 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルで検知。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して接続・初期化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアントは BrokerClientFactory を経由して生成。
    - ExecutionEngine を別スレッドで実行し、停止フラグで安全に停止。
    - PID ファイルの扱いおよび停止時の後処理を含む。
- 設定管理・自動.envロード
  - config.py:
    - プロジェクトルート（.git または pyproject.toml）を基に .env 自動読み込み機能を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパース機能を強化（export プレフィクス、シングル/ダブルクォート、エスケープ、コメント扱いの細かい処理をサポート）。
    - Settings クラスを追加し、環境変数の取得・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。
    - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）を Path オブジェクトで解決。
- 設定ウィザード・検証 CLI
  - config_setup.py:
    - 対話式ウィザードで .env を生成・更新する CLI を追加（項目定義、既存値の再利用、シークレットマスク、保存確認など）。
  - validate_config.py:
    - .env および config/*.yaml の基本的な整合性チェック CLI を追加。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告出力。
    - 本番（KABUSYS_ENV=live）向けのガードチェック（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の注意喚起）。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（daily, 30 日バックアップ）を設定する共通ユーティリティを追加。
    - ログディレクトリ（LOG_DIR）・ログレベル（LOG_LEVEL）の優先解決ロジックを実装。ファイル出力に失敗した場合はコンソールのみで継続。
  - utils/process_priority.py:
    - psutil を用いたプロセス優先度設定ユーティリティを追加（Windows / POSIX の違いを吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境では警告ログを出してスキップする安全設計。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全ゼロ時は等金額配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を行う apply_sector_cap を実装（既存保有のエクスポージャー計算、sell_codes を考慮）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。
  - portfolio/position_sizing.py:
    - position sizing ロジックを実装（allocation_method: "risk_based"/"equal"/"score"）。
    - 単元株（lot_size）丸め、1 銘柄上限・集計上限（aggregate cap）スケールダウン、cost_buffer を考慮した保守的見積りを実装。
    - 端数処理で残余キャッシュを fractional 残差に基づき再配分するアルゴリズムを実装。
- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し、閾値（稼働率 >= 99% 等）で PASS/FAIL を判定するレポートを追加。
    - P95 の計算、日付範囲指定（--from/--to）、DB 存在チェック、エラー時のフォールバック動作を実装。
- 研究用ファクタ計算（部分実装）
  - research/factor_research.py:
    - Momentum 等のファクタ計算のための設計および一部実装（horizon 定数等）を追加。DuckDB 接続を受けて prices_daily / raw_financials を利用する設計。

### Changed
- ログ出力先の扱い
  - ログの標準ストリームに stdout を採用（cron / Task Scheduler などで stdout/stderr を一本化して扱いやすくするため）。
- .env の読み込み順
  - OS 環境 > .env.local > .env の優先順位で読み込む挙動を採用（.env.local は OS 環境変数を保護しつつ上書き可能）。
- run_monitoring/run_execution の起動時共通処理
  - 起動時に set_process_priority("high") を最初に呼ぶことで優先度を高める処理を標準化。

### Fixed
- .env パーサーの堅牢性向上
  - export プレフィクスやクォート内のエスケープ、インラインコメントの扱いなど、実運用で遭遇する様々な .env 形式に対応。
- run_monitoring のポーリング間隔取得の堅牢化
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）だった場合は警告を出してデフォルトにフォールバックするよう修正（time.sleep に渡す際の ValueError を防止）。

### Documentation
- 各モジュールに docstring を付与して使用方法・設計意図を明記（例: run_* スクリプト、config_setup、portfolio/position_sizing など）。
- config_setup による .env 初期化手順と validate_config による事前検証フローを推奨（ウィザード実行 → 設定検証）。

### Security
- .env は絶対に Git にコミットしない旨を config_setup の生成コメントに明記。

### Known issues / Notes
- 一部モジュール（例: research/factor_research.py）はまだ実装途中（ファイル末尾で切れている関数実装など）。今後のリリースで機能追加・完成化予定。
- process_priority / set_cpu_affinity は権限やプラットフォーム差により設定に失敗する場合があり、失敗時は警告をログ出力してスキップする設計となっています。
- position_sizing の価格欠損（price が 0.0 など）によりエクスポージャーが過小見積りされる可能性がある旨の TODO コメントあり。フォールバック価格の利用等を将来検討。

---

このリリースは初期の機能セットを含むもので、実運用に入れる前に以下を推奨します。
- python -m kabusys.config_setup で .env を作成
- python -m kabusys.validate_config で設定を検証（本番では --strict を検討）
- ログディレクトリへの書き込み権限・psutil のインストール状況を確認

※ さらに詳しい設計方針やアルゴリズムの背景は各モジュールの docstring / コメントを参照してください。