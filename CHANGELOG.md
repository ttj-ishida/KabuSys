# Changelog

すべての変更は「Keep a Changelog」形式に従い、Semantic Versioning に準拠します。
このファイルはリリース履歴を人間が読みやすくまとめたものです。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（後方互換性に注意）
- Fixed: バグ修正
- Removed / Deprecated / Security: 該当する場合に記載

なお、リリース日にはこのコードベースのスナップショット日を使用しています。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

Added
- 基本アプリケーション構成を追加
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として設定。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（実運用/モックの切替）。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag により外部停止制御が可能。
    - 実行中の PID を data/execution.pid に記録（pid_file パラメータを受け取る）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視 DB の一貫性を確保）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
- 設定管理
  - config.py:
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出し、.env/.env.local を読み込む。OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーシングは export 形式・クォート・エスケープ・インラインコメント等に対応する堅牢な実装に。
    - Settings クラスを提供し、J-Quants / kabuAPI / DB パス / 各種閾値等をプロパティで取得可能。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。
    - KABUSYS_ENV の検証（development|paper_trading|live）とログレベルの検証。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式の .env ウィザードを実装（.env の初期作成・更新を支援）。
    - 各設定項目の説明、デフォルト表示、シークレット項目のマスク表示、保存確認機能を提供。
  - validate_config.py: 起動前に .env および config/*.yaml の設定検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config YAML の存在・パース検証、KABUSYS_ENV=live 時の追加ガード等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ログ / プロセスユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定する共通ユーティリティ。
    - LOG_DIR 指定やディレクトリ作成失敗時のフォールバック（ファイル出力無効化）に対応。
    - stdout を用いることでスケジューラからのリダイレクト運用を容易化。
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する関数を提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足や未対応環境は警告を出してスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア順で候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクターエクスポージャーを計算し、閾値超過セクターの候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告の上で 1.0 をフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に従った発注株数決定ロジック。
      - 単元（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer（手数料/スリッページ見積り）加味等に対応。
      - risk_based モードではポジションあたりリスク（risk_pct）と損切り率（stop_loss_pct）から株数計算。
- ツール / レポート
  - tools/paper_verification_report.py:
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - しきい値（PASS/FAIL 判定）を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。
    - --from / --to / --db オプションで期間・DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先的に利用。
- Research
  - research/factor_research.py:
    - ファクター計算モジュール（モメンタム/ボラティリティ/バリュー/流動性等）を追加。DuckDB を介して prices_daily / raw_financials のみを参照する設計。
    - 本バージョンではモメンタム計算の実装が開始されており、設計・定数が含まれる（注: ファイルは途中までの実装）。

Changed
- DB の扱いに関する設計方針を明文化
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視の一貫性確保のため）。
  - 実行（execution）は paper_trading 環境であれば paper_sqlite_path に切り替え、本番データと完全に分離する。
- ロギング既存ハンドラをクリアしてから再設定するように変更（重複ハンドラ防止）。

Fixed
- .env パーサーの改良
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを適切に処理するよう改善。
- ログディレクトリ作成失敗時の挙動を明確化（ファイル出力をスキップし、標準出力のみで継続）。

Security
- .env の取り扱いに関する注意書きを config_setup のヘッダーに明記（.env を絶対に Git 管理下に置かないこと）。

Notes / Migration
- 環境変数の自動ロードはデフォルトで有効（プロジェクトルートを検出できない場合はスキップ）。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings のプロパティは妥当性チェックを行い、不正値の場合は ValueError を送出します。特に KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値に注意してください。
- run_monitoring / run_execution は起動時にプロセス優先度を "high" に設定しようとします。権限不足やプラットフォーム非対応時は警告を出してスキップします。
- paper_trading 用 DB のデフォルトは data/paper_trading.db、監視 DB のデフォルトは data/monitoring.db、分析用 DuckDB のデフォルトは data/kabusys.duckdb です。必要に応じて環境変数で上書きしてください。
- tools/paper_verification_report のしきい値は static 定義されています。必要ならばスクリプトをコピーして基準値を調整してください。

Known limitations / TODO
- research/factor_research.py は初期の実装途中（モメンタム計算の途中まで）。完全実装および単体テストが必要。
- position_sizing の lot_size は全銘柄共通で固定。銘柄別の単元対応（マスタ参照）に拡張予定。
- apply_sector_cap の価格欠損（price=0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。価格フォールバックロジックの追加が望ましい。

---

[0.1.0]: https://example.org/releases/0.1.0 (placeholder)