# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に基づく初回リリースを記載しています。

## [Unreleased]
（現在の差分: なし — 次回リリースの変更はここに記載してください）

## [0.1.0] - 2026-04-18
初回公開リリース

### Added
- 起動用スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視データは環境にかかわらず本番 sqlite_path を使用する（監視専用テーブルの初期化を実行）。

- 設定・環境管理
  - config.py
    - 環境変数の読み取りを一元化する Settings クラスを実装。
    - プロジェクトルート自動検出 (_find_project_root) による .env 自動読み込み（.env, .env.local。OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env のパースが export 形式・クォート・エスケープ・インラインコメントなどに対応。
    - 主要設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 周りの設定 / 監視閾値 / 環境判定など）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）・paper_sqlite_path の分離。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を実装。
    - デフォルト値、選択肢、シークレット入力のマスク表示機能を提供。
    - .env を安全に生成するテンプレート出力機能を提供（.env を絶対に Git にコミットしない旨の注記を含む）。

- 設定検証
  - validate_config.py
    - .env および config/*.yaml の事前チェック用 CLI を実装。
    - 必須環境変数の未設定/プレースホルダ検出、KABUSYS_ENV の妥当性チェック、ログレベルの検証、DB パスの親ディレクトリチェック、YAML の存在とパース（PyYAML 未インストール時に警告）等を行う。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス設定ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを実装。
    - LOG_LEVEL / LOG_DIR / app_name / level 引数で挙動を制御可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
    - 標準エラーではなく標準出力（stdout）へ出力する設計。
  - utils/process_priority.py
    - プラットフォーム差を吸収してプロセス優先度（high/normal/low）を設定する関数を実装（Windows/POSIX に対応）。
    - CPU affinity を特定コア数に固定する set_cpu_affinity を実装（存在しない場合は安全にスキップ）。
    - 権限不足や未対応環境時には警告ログを出して継続する堅牢性を確保。

- ポートフォリオ構築・資金配分ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート・候補選定 select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額配分にフォールバックする警告を出す）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して新規候補を除外するロジック。既存保有のエクスポージャ計算、売却予定の除外、unknown セクターの扱いを実装。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。
    - 単元株（lot_size）で丸め、per-position の上限（max_position_pct）と aggregate cap（available_cash）でスケールダウンする実装。
    - cost_buffer による手数料・スリッページ見積りを反映した保守的な計算。端数配分は再現性のある優先度で割当て。

- 研究用ファクター計算
  - research/factor_research.py
    - ファクター計算モジュール（Momentum / Value / Volatility / Liquidity 設計）。DuckDB 接続を受けて prices_daily / raw_financials を参照し結果を返す設計。モメンタム用の定数・インターフェース（calc_momentum）を導入（実装の続きあり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）を算出。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL 判定を行う。
    - --from/--to/--db オプションで期間・DB を指定可能。DB が存在しない場合はエラーメッセージを出力。

- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン番号 __version__ = "0.1.0" を追加。

### Changed
- ログ出力のデフォルト先を stdout に明示（cron/Task Scheduler と連携しやすくするため）。
- .env 読み込みの優先順位を明確化（OS 環境 > .env.local > .env）。.env.local は OS 環境の保護を維持しつつ上書き可能。
- run_monitoring と run_execution の挙動を明確化（停止フラグと PID 管理、DB の選択ルール等）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（非整数、0以下）に対してデフォルトへフォールバックし、警告ログを出すように改善（run_monitoring）。
- PAPER_FILL_MODE の無効値検出を追加し、明示的なエラーを投げるようにして設定ミスを早期に検出（config.Settings）。
- .env 読み込みでファイルアクセスエラーが発生した場合に警告を出して安全に続行するように（config._load_env_file）。

### Security
- .env ファイルを絶対に Git にコミットしない旨の注意書きを config_setup の出力に追加。
- 必須環境変数が未設定の場合は validate_config でエラー検出するようにし、運用時の初期設定ミスを低減。

### Notes / Misc
- DuckDB と SQLite の利用方針
  - DuckDB は分析用の永続ストレージ（config の DUCKDB_PATH）として使用。
  - 監視・トレードログは SQLite（config の SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）に記録。paper_trading 実行時は paper_sqlite_path を使用して本番データと分離。
- 実装上のいくつかの TODO / 注意点をコード内に記載
  - position_sizing: price 欠損時のフォールバック価格（前日終値・取得原価など）の導入を検討中。
  - risk_adjustment: "unknown" セクターはセクター上限の適用対象外としている点に注意。
  - research/factor_research の calc_momentum はファイル末尾で未完（途中実装あり）。

---

この CHANGELOG はコードの内容およびコメントから推測して作成しています。実際のリリースノートとして使用する際は、実装責任者による確認・調整を推奨します。