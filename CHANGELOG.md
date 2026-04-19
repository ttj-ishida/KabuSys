# CHANGELOG

すべての利害関係者に対して、変更内容を分かりやすく伝えるために Keep a Changelog の慣習に準拠しています。

注: 以下の変更履歴は提供されたコードベースの内容から推測して作成した初回リリース向けのまとめです。

## [0.1.0] - 2026-04-19
初回リリース

### 追加 (Added)
- 実行／監視の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（デフォルト: data/paper_trading.db）。
    - ブローカークライアント生成（BrokerClientFactory）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を実行。
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) の扱い。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグによる終了処理を実装。

- 環境・設定管理機能を追加
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env のパースは export プレフィックス、クォート、インラインコメントに対応。
    - Settings クラスで環境変数に基づく型安全なプロパティを提供（DB パス、ログレベル、各種しきい値、環境判定フラグなど）。
    - PAPER_FILL_MODE 等の値検証を実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成 / 更新を支援。
    - シークレット項目はマスク表示、選択肢やデフォルトのサポート、保存前の確認ダイアログを提供。

  - validate_config.py
    - 起動前チェック CLI。必須環境変数や設定ファイル、DB パス、KABUSYS_ENV の妥当性などを検証。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML の有無に応じて config/*.yaml の検証をスキップ／実行。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ計算のみ）
  - portfolio/portfolio_builder.py
    - 銘柄選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier。
  - portfolio/position_sizing.py
    - position sizing の主要ロジック。allocation_method（risk_based / equal / score）対応、lot_size（単元株）丸め、aggregate cap によるスケーリング、コストバッファ考慮。
  - portfolio/__init__.py で上記 API をエクスポート。

- ユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに対する一貫したロギング設定ユーティリティ。コンソール出力（stdout）と日次ローテートファイル（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成、既存ハンドラのクリーンアップ、環境変数/引数からレベルや出力先を決定。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows の priority class、POSIX の nice 値）、CPU affinity 設定ユーティリティを提供。
    - 権限不足などの失敗は警告でスキップする設計。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite (PAPER_TRADING_SQLITE_PATH) から各種指標（稼働率・注文成功率・送信率・レイテンシ(P95) 等）を集計してレポート出力。
    - デフォルトの合格基準（稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 <= 200ms）を実装。
    - コマンドライン引数 --from / --to / --db をサポート。

- 研究用ファクター計算基盤の追加（骨組み）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity の計算方針を実装するための基盤を用意（DuckDB 接続受け取り、prices_daily/raw_financials 想定）。
    - モメンタム計算関数（calc_momentum）などの骨組みを含む（※ ファイルは一部で切れており、完全実装は今後）。

- パッケージメタ情報
  - __init__.py にてバージョンを定義: __version__ = "0.1.0"

### 変更 (Changed)
- なし（初回リリースのため既存コードの変更履歴はなし）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制約・注意点 (Known issues / Notes)
- apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りされ正しくブロックされない可能性がある旨の TODO コメントあり。前日終値などのフォールバック価格の導入を検討。
- position_sizing:
  - 単元株単位（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_size をサポートする旨の TODO がある。
- run_monitoring:
  - 監視は環境にかかわらず Settings.sqlite_path（本番用）を使用する設計。意図的な仕様だが運用時は注意。
- process_priority / set_cpu_affinity:
  - 実行環境の権限や OS により効果が出ない場合がある（AccessDenied 等） — その場合は警告を出してスキップする。
- logging_setup:
  - ログディレクトリ作成に失敗するとファイル出力を無効化し、コンソールのみで継続。
- research/factor_research.py:
  - ファイルが途中で切れており（calc_momentum の途中）、完全実装は未完。利用前に完成実装が必要。

### マイグレーション / 運用メモ (Migration / Operational notes)
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの .env を自動読み込みします。テストなどで自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の作成:
  - 初回セットアップは python -m kabusys.config_setup を推奨。生成後は python -m kabusys.validate_config で検証してください。
- paper_trading の分離:
  - paper_trading 実行時には PAPER_TRADING_SQLITE_PATH（または Settings.paper_sqlite_path デフォルト data/paper_trading.db）が使用され、本番の monitoring DB と分離されます。
- 実行開始前に kill/s top フラグの確認:
  - run_execution と run_monitoring はプロジェクト内 data/stop_requested.flag をチェックして起動/停止の制御を行います。運用時のフラグ管理に注意してください。
- ログ:
  - デフォルトログディレクトリは logs/、各アプリケーションごとに日次ローテーションで logs/<app_name>.log に保存します。ログレベルは LOG_LEVEL 環境変数で制御可能。

---

今後の予定（提案）
- research/factor_research の完全実装（duckdb クエリおよび正規化処理）。
- 銘柄個別の lot_size 対応、価格フォールバックロジックの追加。
- テストカバレッジ拡張、および CI での validate_config チェック組み込み。
- モニタリング・アラートの LINE 通知連携の実装強化（本番環境での LINE 設定必須）。
- ExecutionEngine 側の詳細なログ・メトリクス出力の強化。

もし、より細かい変更履歴（ファイル単位の diff に基づく詳細）や別バージョン区切りが必要であれば、対象となるコミット履歴や差分を提供してください。