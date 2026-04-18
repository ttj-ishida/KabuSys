# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。本リリースはシステム全体の起動スクリプト、設定管理、ログ/プロセスユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツールなどの基本機能を提供します。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 設定管理
  - 環境変数/`.env` ファイル読み込みを行う設定モジュール（src/kabusys/config.py）を追加。
    - プロジェクトルートを .git または pyproject.toml から検出して自動で `.env` / `.env.local` を読み込む（無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - export 付き行やクォートされた値、インラインコメント処理に対応した .env パーサ実装。
    - Settings クラスにより各種設定（J-Quants、kabuステーション、DB パス、Paper Trading 関連、監視閾値、実行環境フラグなど）をプロパティで提供。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV/LOG_LEVEL の検証を実装。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）、pid/kill flag パス等を設定で取得可能。

- 設定ウィザード・検証
  - 対話式 .env 作成/更新ウィザード（src/kabusys/config_setup.py）を追加。
    - シークレット入力のマスク、既存値の再利用、選択肢指定、保存確認などの対話フローを提供。
    - .env のテンプレート生成ロジックを備える。
  - 起動前チェック CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パースチェック（PyYAML 利用）など。
    - --strict モードで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - duckdb を分析用に接続。
    - 起動時にプロセス優先度を "high" に設定。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper trading SQLite を使用して本番 DB と分離（settings.paper_sqlite_path）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient 想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine 等の組立てと実行管理。
    - 停止フラグ検知でエンジン停止、実行用 pid ファイル管理（data/execution.pid）。

- 監視・モニタリング
  - 監視 DB 初期化関数参照（init_monitoring_db を起動スクリプト内で呼び出し、監視テーブルの存在を保証）。
  - monitoring 用 SystemMonitor の単一チェック呼び出し（monitor.check_once）をポーリングループで実行（例外はキャッチして次サイクルへ）。

- ロギング
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装、既存ハンドラのクリーンアップ処理を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ファイルハンドラ生成失敗は警告ログを出力。

- プロセス優先度 / CPU affinity
  - クロスプラットフォーム対応ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows/Linux/Mac (POSIX) に対応した優先度設定（psutil を利用）。
    - set_process_priority(level) で "high"/"normal"/"low" を設定。権限不足時は警告でスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアに固定可能（例外は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（score, signal_rank によるタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額にフォールバック（WARNING）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率が上限を超える場合、新規候補からそのセクターを除外（"unknown" セクターは制限適用外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対して 1.0/0.7/0.3 を返す（未知レジームは 1.0 でフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき各銘柄の発注株数を算出。
      - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct を考慮した逆算方式。
      - equal/score: ウェイトに応じた配分、per-position 上限 (max_position_pct)、aggregate 利用可能資金 (available_cash)、lot_size（デフォルト 100）で単元丸め。
      - cost_buffer により手数料・スリッページ分を保守的に見積もり、合計コストが available_cash を超える場合はスケールダウンして丸め直し、残余キャッシュで端数配分を試行。
      - 価格が取得できない銘柄はスキップ。

- 研究用ファクター計算（研究モジュール）
  - ファクター計算モジュール骨格（src/kabusys/research/factor_research.py）を追加。
    - Momentum, Value, Volatility, Liquidity に基づく計算フレームを想定（DuckDB の prices_daily / raw_financials を参照）。
    - P95 等の集計ユーティリティなどの設計方針を実装。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - SQLite（デフォルト data/paper_trading.db）を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計。
    - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH での上書き可）。
    - Pass/Fail 判定基準（デフォルト値）:
      - 稼働率 >= 99.0%
      - 注文成立率 (fill_rate) >= 90.0%
      - 送信率 (send_rate) >= 95.0%
      - P95 レイテンシ <= 200 ms

- その他
  - tools パッケージ初期化ファイルを含む。

### Changed
- 初期リリースのため、特別な変更履歴はなし。

### Fixed
- 初期リリースのため、特別な修正履歴はなし。

### Security
- シークレット系項目（J-Quants リフレッシュトークン、kabu API パスワード、LINE トークン）は .env ウィザードでマスク入力/マスク表示を行い、.env を絶対に Git に含めない旨の注意文を出力。

---

注記:
- 起動スクリプトは外部コンポーネント（BrokerClientFactory、ExecutionEngine、SystemMonitor 等）に依存します。本 CHANGELOG はコミットに含まれるソースコードからの推測に基づいて作成しています。
- 実行環境や運用時の挙動（特にプロセス優先度設定やファイルアクセス権）は OS/権限に依存します。