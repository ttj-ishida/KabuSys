# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

### Added
- —（なし）

---

## [0.1.0] - 2026-04-25

初回リリース。以下の主要機能・ユーティリティを追加しました。

### Added
- 実行用エントリスクリプト
  - run_monitoring.py
    - SystemMonitor を用いたポーリング監視ループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag により制御。
    - 監視用 SQLite は KABUSYS_ENV に依らず本番（設定された sqlite_path）を使用。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用（分離された）Paper Trading SQLite DB を使用（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、Engine をスレッドで実行。停止フラグで安全に停止可能。
    - 実行中の PID 管理（data/execution.pid）に対応。

- 設定・環境管理
  - config.py
    - .env/.env.local の自動ロード機構（プロジェクトルートの検出: .git または pyproject.toml 基準）。
    - .env のパース実装は export 文やクォート、インラインコメント等に対応。
    - Settings クラスを通じてアプリ設定にアクセス可能（J-Quants、kabu API、DB パス、監視閾値、環境判定等）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等のプロパティを提供し、妥当性チェック（例: PAPER_FILL_MODE の有効値チェック）を行う。

- 設定ツール / 検証ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。既存値の再利用、シークレットマスク表示、保存確認を実装。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数の存在チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス（親ディレクトリ存在）や config/*.yaml の有無／パース検証を行う。
    - --strict オプションで警告を FAIL 扱いに変更可能。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未登録や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足等は警告を出してスキップ）。
    - psutil を利用し、例外ハンドリングで安全に動作。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。スコア総和が 0 の場合は等金額にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づき候補を除外（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market レジーム(bull/neutral/bear) に対する投下資金乗数を返す（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数計算。
    - 単元株（lot_size）丸め、per-position 上限 max_position_pct、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残余キャッシュ分の端数配分ロジックを実装。
    - price 欠損や価格 0 の場合はログ出力してスキップ。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH）からデータを集計し、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等を算出してレポート出力。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、Pass/Fail 判定を行う。
    - SQL 抜けやテーブル未存在時のフォールバック処理を実装。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - Momentum や MA、ATR、流動性等の計算を行うための定数・calc_momentum 等の骨格実装（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。

### Changed
- パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

### Notes / Known limitations
- apply_sector_cap:
  - price_map に 0.0（欠損）があるとエクスポージャーが過少見積りになり、期待通りブロックされない可能性がある旨の TODO コメントあり（将来的にフォールバック価格導入を検討）。
- position_sizing:
  - 現状 lot_size はグローバル固定（将来的に銘柄別 lot_map での拡張を予定）。
- run_monitoring / run_execution:
  - 実際の SystemMonitor / ExecutionEngine の内部実装やブローカークライアントの実装は別モジュールに依存（このリリースには参照・初期化コードを含むが詳細は別ファイル）。
- .env 自動ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップ。自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

### Security
- 本リリースではシークレット（トークン・パスワード）を .env に保存する設計のため、.env を絶対にリポジトリにコミットしないことを強調（config_setup のヘッダに記載）。

---

今後の変更案内（予定）
- 各コンポーネント（SystemMonitor / ExecutionEngine / BrokerClient 等）の機能拡充・テスト追加。
- ファイル・DB 周りの堅牢化（権限エラー/ロック対策）と監視アラートの強化。
- position_sizing の銘柄別単元対応、価格フォールバック機構の追加。

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実装の詳細や変更履歴の厳密な追跡にはコミット履歴を参照してください。）