# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初期リリースに相当する変更点を、コードベースから推測してまとめました。

フォーマット:
- Added: 新規追加機能・モジュール
- Changed: 既存振る舞いの変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当なしの場合は省略

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-18

### Added
- 初期実装のコア機能一式を追加。
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。
- 実行・監視用エントリポイントスクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。プロセス優先度の設定、DB 接続、Broker クライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）の監視、PID ファイル管理などを実装。
    - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）にデータを分離して記録する挙動を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化（init_monitoring_db）、停止フラグ検出による安全終了、例外時のログ記録を実装。
    - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する仕様を明示。
- 設定・環境変数管理を提供。
  - config.py
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から探索）を実装。優先順位: OS 環境 > .env.local > .env。
    - .env 行パーサーは export プレフィックス、クォート／エスケープ、インラインコメントを考慮した堅牢な実装。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値 / 環境種別（development/paper_trading/live）などの設定プロパティを集約。値検証（有効値チェック、必須チェック）を行う。
- 設定ウィザードと検証ツールを追加。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI。シークレット値は表示をマスク。保存前に確認プロンプトを表示。
  - validate_config.py: .env や config/*.yaml の存在・基本妥当性検証を行う CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリチェック、PyYAML がなければ YAML 検証をスキップする挙動等を実装。--strict オプションで警告を FAIL 扱いに可能。
- ロギングおよびプロセス制御ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（デイリーローテーション）を設定する共通セットアップ。ログレベル・ログディレクトリの解決順やエラーハンドリング（ディレクトリ作成失敗時はファイル出力をスキップ）を実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。権限不足や未対応 OS の場合は警告を出して安全にフォールバック。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ計算）。
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順で上位 N 選択）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限を超える場合に新規候補を除外）、calc_regime_multiplier（market regime に応じた投下資金乗数: bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes（allocation_method: risk_based / equal / score を実装）。単元株丸め、per-position 上限、aggregate cap のスケールダウン処理、cost_buffer（手数料・スリッページ見積）考慮、残余キャッシュの再配分ロジックを実装。lot_size 固定（現状 100）を前提にしているが将来的な拡張用の TODO を記載。
- リサーチ（ファクター計算）モジュールの骨組みを追加。
  - research/factor_research.py
    - モメンタム・ボラティリティ・流動性・Value 系ファクターの計算方針と定数を定義。DuckDB 経由で prices_daily / raw_financials を参照して計算する設計。モメンタム計算関数（calc_momentum）の開始実装が含まれる（※一部ファイル切断あり）。
- ツール類を追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率/送信率、API レイテンシ、リスク却下数）を集計して検証レポートを出力。閾値を基に PASS/FAIL を判定。P95 計算や日付フィルタ (--from/--to / --db オプション) に対応。
- DB/監視初期化ユーティリティ参照箇所を導入（init_monitoring_db 呼び出し）。
- 各種デフォルトパス・環境変数名をドキュメント的に整備（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR, MONITOR_POLL_INTERVAL, KILL_FLAG_CLEAR_ON_START など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known limitations
- research/factor_research.calc_momentum の実装はファイル末尾で途切れており、完全実装ではない可能性があります（今後の実装継続が必要）。
- portfolio/position_sizing の lot_size は現状グローバル共通設定（デフォルト 100）を前提としており、銘柄別単元対応は TODO コメントで予定されています。
- apply_sector_cap は price が欠損（0.0）だった場合に露出が過小評価される可能性がある点を TODO として記載しています（価格フォールバックが未実装）。
- utils/process_priority の優先度設定は OS/権限に依存し、設定に失敗した場合は警告を出してスキップします。
- utils/logging_setup はログディレクトリ作成に失敗した場合にファイルログを無効化して stdout のみで継続します。
- validate_config は PyYAML 非依存運用を許容し、未インストール時は YAML 検証をスキップして警告を出します。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」仕様になっています。環境に依存させたくない設計意図のようですが、利用時は意図的であることを確認してください。
- run_execution は paper_trading モード時に paper_trading 用 DB を使用して本番 DB と完全分離する仕様を採っています。Paper トレードの挙動（MockBroker の動作・fill_mode 等）は設定値（PAPER_FILL_MODE）に依存します。

### Migration / Usage notes
- .env はリポジトリにコミットしないこと（config_setup.py で生成される .env にはその旨のヘッダが入っています）。
- 起動前に `python -m kabusys.config_setup` で .env を作成し、`python -m kabusys.validate_config` で検証することを推奨します。
- Paper Trading を行う場合は KABUSYS_ENV を `paper_trading` に設定し、必要なら PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE を設定してください。
- 監視プロセスのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で制御可能（単位: 秒、1 以上）。不正な値はデフォルト 60 秒にフォールバックします。
- ログの保管先・レベルは LOG_DIR / LOG_LEVEL 環境変数で上書きできます。

---

（本 CHANGELOG はソースコードの内容から推測して作成しています。実運用にあたっては実装の追加・変更ログやコミット履歴を参照してください。）