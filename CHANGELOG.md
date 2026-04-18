# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。

最新リリース
------------

### [0.1.0] - 2026-04-18

Added
- 全体
  - パッケージ初期リリース。基本的な自動売買・検証・運用補助ツール群を追加。
  - バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" にて管理。

- 設定・環境変数関連
  - Settings クラスを追加して環境変数から設定を一元管理（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB パス /監視閾値 /実行環境 (KABUSYS_ENV) /ログレベル等のプロパティを提供。
    - KABUSYS_ENV の妥当性検証（development, paper_trading, live）や LOG_LEVEL の検証を実装。
    - paper_trading 用の DB パス（paper_sqlite_path）と PAPER_FILL_MODE の検証ロジックを追加。
  - 自動 .env ロード機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。.env と .env.local の読み込み順と OS 環境変数保護を実装。
  - 高度な .env パーサ実装（引用符内のエスケープや export 形式対応、インラインコメント処理など）。

- 設定支援 CLI
  - 対話式の環境設定ウィザードを追加（python -m kabusys.config_setup）。.env の初期作成・更新を支援（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML インストール時）などを検査。--strict オプションで警告も失敗扱いにできる（src/kabusys/validate_config.py）。

- 実行 / 監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB（data/paper_trading.db）と MockBrokerClient を使って本番 DB と完全に分離。
    - プロセス優先度（High）設定、PID ファイル管理、停止フラグ検知、スレッドでの engine 実行と安全停止処理を実装。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit 等）を組み込んだ組み立てロジックを実装。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）の検知によるループ終了、例外発生時はログ出力して次ポーリングへ継続。

- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - LOG_DIR 指定またはデフォルト logs/、ファイルハンドラ作成に失敗した場合はコンソールのみで継続するフォールバックを実装。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収して優先度設定を実施。失敗時は警告を出して安全にスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定可能（許容範囲チェック付き）。

- ポートフォリオ構築
  - 銘柄選定・配分計算モジュール（pure functions）を追加（src/kabusys/portfolio/*）。
    - select_candidates: スコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア全てが 0 の場合のフォールバックを含む）。
    - apply_sector_cap: セクター集中上限チェックと候補除外（sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定、lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り。

- Paper Trading 検証ツール
  - paper_trading 用の検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs などを参照して稼働率・注文成功率・送信率・レイテンシ(P95) 等を算出し PASS/FAIL 判定を表示。
    - デフォルト DB パスは data/paper_trading.db、--db で上書き可能。閾値はスクリプト内定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。

- リサーチ（ファクター計算）
  - ファクター計算モジュール（momentum など）を追加（src/kabusys/research/factor_research.py）。
    - DuckDB 接続を受けて prices_daily / raw_financials から Momentum / Value / Volatility / Liquidity を計算する設計（モジュールは実装途中の部分あり）。

Changed
- ロギング
  - Console 出力に stdout を使用（stderr ではなく）：cron / Task Scheduler 等からのリダイレクト運用を想定して一本化。

Fixed / Improved
- .env 読み込みの堅牢化
  - export 形式・クォート・エスケープ・コメント処理などに対応し、より現実的な .env の記法に対応（src/kabusys/config.py）。
  - .env.local を .env より優先して上書き（ただし OS 環境変数は保護）。
- validate_config
  - PyYAML が未インストールでも警告を出して YAML 検証をスキップするようにし、依存がない環境でも実行可能に。
  - 本番（live）時の追加ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）を追加。
- プロセス優先度・CPU affinity
  - 未対応 OS やアクセス権限不足時に例外でクラッシュしないよう警告ログで安全にスキップする振る舞いに改善。

Notes
- セキュリティ／運用
  - .env ファイルは絶対に Git にコミットしない旨の注意書きを config_setup のヘッダに追加。
  - 本番運用時は KABUSYS_ENV=live の扱いに注意（validate_config が警告を出します）。
- 既知の未完事項
  - src/kabusys/research/factor_research.py はモジュール方針と多くの実装が含まれているがファイル末尾で実装途中の箇所が存在します（継続実装予定）。
  - 将来的に lot_size を銘柄毎に管理する拡張や、価格欠損時のフォールバックロジック（前日終値等）を導入予定。

Deprecated
- なし

Removed
- なし

Security
- なし

(注) 上記はコードベースから推測して作成した CHANGELOG です。今後のコミットに合わせて各項目の粒度や日付を更新してください。