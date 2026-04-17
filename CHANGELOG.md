# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、以下の変更点は提供されたコードベースから推測して記載しています。

## [Unreleased]

（現在のブランチ / 次バージョン向けの未リリース変更はここに記載してください）

---

## [0.1.0] - 2026-04-17

初回リリース。自動売買システム KabuSys のコアユーティリティ、設定管理、実行・監視エントリポイント、ポートフォリオ構築ロジック、研究用ファクター計算、ペーパートレード検証レポートなどを含む。

### Added
- 基本メタ情報
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。

- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（MockBrokerClient を含む想定）。
    - Engine の起動に先立ちプロセス優先度を "high" に設定。
    - 停止フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) に対応し、フラグ検出時に安全に停止する仕組みを提供。
    - RiskManager のデフォルト設定を組み込み（max_position_pct, max_utilization, rate limits, circuit breaker など）。initial_portfolio_value を broker.get_available_cash() で初期化。

  - run_monitoring.py
    - SystemMonitor を周期的にポーリングする監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず設定された本番 sqlite_path を使用して監視 DB を初期化／接続。
    - 停止フラグファイルによる終了検知と例外時のログ捕捉を実装。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env, .env.local の読み込み順序と OS 環境変数保護（protected）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能あり。
    - .env 行のパーサーを実装：export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理（クォートなしでは空白の直前の # をコメントとみなす）に対応。
    - Settings クラスで環境変数の取得とバリデーションを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須チェック、KABUSYS_ENV・LOG_LEVEL の有効値チェック、各種パスや閾値の型変換）。
    - Paper Trading 関連設定: PAPER_FILL_MODE（instant/partial/never/reject）、PAPER_TRADING_SQLITE_PATH。

  - config_setup.py
    - .env 生成・更新の対話式ウィザードを実装。既存 .env 読み込み、選択肢提示、シークレット入力（マスク表示）をサポート。
    - 生成される .env のテンプレートを書き出すユーティリティを提供。

  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ有無チェック、YAML パース（PyYAML がなければ警告）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群、DB不参照）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算。全銘柄スコアが 0 の場合は等配分にフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を基にセクターごとのエクスポージャーを計算し、セクター上限（max_sector_pct）を超える場合は同セクター新規候補を除外。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market regime（"bull"|"neutral"|"bear"）に応じた投下資金乗数（1.0/0.7/0.3）。未知レジームは警告とともに 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数計算、lot_size(例:100) 単位で丸め、単銘柄上限・aggregate cap（available_cash）に応じたスケーリングと余剰配分アルゴリズムを実装。
    - risk_based の場合はリスク許容率とストップロスからベースシェアを算出。
    - cost_buffer を加味した保守的なコスト見積もり（スリッページ・手数料相当）。

- 研究／ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルからファクターを計算する純粋関数群を実装。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR）、流動性指標などを計算する calc_momentum / calc_volatility 等を追加。
    - 計算ウィンドウやスキャン日数に関する定数化。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority class）設定ユーティリティを追加。Windows と POSIX（Linux, Darwin, FreeBSD）を吸収する実装。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対しては警告を出して安全にスキップ。

- 監視 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を実行して監視テーブルの冪等な初期化を行う呼び出しを run_* スクリプトで統一している（監視テーブルが存在することを保証）。

- ペーパートレード検証レポート
  - tools/paper_verification_report.py
    - ペーパートレードの SQLite DB（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシなど）を集計して人間向けレポートを出力する CLI を追加。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義して PASS/FAIL 判定を行う。
    - 日時フィルタ（--from, --to）と --db オプションをサポート。欠損テーブルに対しては安全に N/A / 0 を扱う。

### Changed
- 環境ファイルロードの動作
  - .env/.env.local の読み込み順と OS 環境変数の保護（既存 OS 環境変数は上書きされない）を明示的に実装。

- DB 接続の扱い
  - 監視（run_monitoring）は KABUSYS_ENV に依らず本番の sqlite_path を使用して監視データを扱う仕様に統一。
  - 実行（run_execution）は paper_trading 時に専用 DB を使用して本番 DB と明確に分離。

### Fixed / Notes
- .env パーサー
  - クォート内のバックスラッシュエスケープや対応する閉じクォートの扱いを実装し、インラインコメントの誤認を低減。
  - クォートなしの値における '#' の扱いは「直前が空白/タブの場合にコメント」として扱う微妙な仕様を導入（既存 .env の書式に注意）。

- プロセス優先度設定の堅牢性
  - psutil に存在しない属性を getattr で安全に扱うことでモジュールロード失敗を回避。
  - アクセス権限不足や未実装 API 発生時は警告ログを出して処理を継続。

- ポートフォリオ計算上の注意点（TODO/警告）
  - apply_sector_cap 内で price が 0.0 の場合はエクスポージャーが過少見積もられる可能性あり。将来的に前日終値等のフォールバックを検討する旨を注記。

### Security
- 機密情報の取り扱い
  - config_setup のウィザードはシークレット項目をマスクして表示（ファイル生成時も .env を Git にコミットしないよう注記）。環境変数の未設定時は明示的に ValueError を投げる必須チェックを導入。

---

今後の改善候補（推奨）
- .env パーサーの仕様をドキュメント化し、既存の .env フォーマットとの互換性を確保するテスト追加。
- portolio / position_sizing の lot_size を銘柄別に扱うための拡張（stocks マスタと lot_map の導入）。
- monitoring と execution の統合テスト、ペーパートレード用のモックブローカーの振る舞いを明示的にテスト。
- YAML 解析のために PyYAML を依存に追加するか、YAML がない場合の代替仕様をドキュメント化。

---

（以上）