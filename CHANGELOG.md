# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
現在のバージョンは 0.1.0（初回リリース）です。

全般なルール:
- フォーマット: https://keepachangelog.com/ja/1.0.0/
- 日付: 2026-04-18

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本フレームワーク
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - プロジェクトルート検出と自動 .env ロード機能を実装（kabusys.config）。
    - 読込順: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。

- 環境設定関連
  - 対話式環境設定ウィザード `kabusys.config_setup` を追加。
    - .env の作成・更新を対話式に支援。
    - 出力フォーマットの標準化とサンプル項目を実装（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース確認、live 環境向けのガードを実装。
    - `--strict` オプションで警告をエラー扱いに可能。

- ログ・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/）を設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL の解決順を実装（引数 > 環境変数 > デフォルト）。
  - プロセス優先度・CPU affinity 管理 `kabusys.utils.process_priority` を追加。
    - クロスプラットフォーム対応（Windows / POSIX）で優先度設定（high/normal/low）を提供。
    - CPU affinity 固定機能（最初 N コア）を提供。権限不足などは警告を出して安全にスキップ。

- 実行・監視エントリスクリプト
  - `kabusys.run_execution` — ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を high に設定。
    - `KABUSYS_ENV=paper_trading` の場合は Mock ブローカーを使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録して本番 DB と完全分離。
    - 実行中停止フラグ（data/stop_requested.flag）および pid 管理（data/execution.pid）に対応。
    - ExecutionEngine 周辺のコンポーネント組立（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定し、初期ポートフォリオ値はブローカー残高から取得。
  - `kabusys.run_monitoring` — SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトにフォールバック。
    - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用（監視データは本番 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。

- 監視・Paper Trading 関連
  - 監視 DB 初期化ユーティリティのフック（monitoring_db.init_monitoring_db の呼び出し）を実装（冪等に保証）。
  - Paper Trading 向け検証レポートツール `kabusys.tools.paper_verification_report` を追加。
    - DB（Paper Trading 用 SQLite）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計してレポート出力。
    - コマンドライン引数で期間指定可能（--from, --to）、--db で DB パス指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。
    - 判定基準（デフォルト閾値）:
      - 稼働率: >= 99.0%
      - 注文成立率 (Fill Rate): >= 90.0%
      - 送信率 (Send Rate): >= 95.0%
      - P95 レイテンシ: <= 200 ms

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio パッケージを追加。DB 非依存の純粋関数で構成。
  - portfolio_builder
    - select_candidates: スコア降順で上位 N を選択（同点時は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等配分にフォールバックして警告を出力）。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター別時価が指定比率を超える場合にそのセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market_regime に応じた資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知のレジームは 1.0 でフォールバック（警告）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、lot_size（単元株）で丸め、コストバッファ考慮の aggregate cap スケーリングを実装。
    - risk_based 方式ではリスク許容率、ストップロス率から基準株数を算出。
    - Aggregate cap 超過時はスケールダウンし、残余現金で端数を lot 単位で再配分。

- リサーチ/ファクター計算
  - kabusys.research.factor_research の骨格を追加（モメンタム・ボラティリティ等の計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計方針を明記。
    - （注）ファイル末尾で計算関数の実装が途中で切れている点に留意。

### 変更 (Changed)
- 初回リリースにあたり内部 API の設計を明確化:
  - ロギング・プロセス優先度設定を全起動スクリプトで統一して呼び出すように実装。
  - DB パスのデフォルトと paper_trading による DB 分離ポリシーを明確化。

### 修正 (Fixed)
- N/A（初回リリースのため既知のバグ修正履歴は無し）。

### 既知の制限・注意点 (Notes / Known issues)
- factor_research.calc_momentum 等の一部リサーチ関数は実装途中（ファイル末尾に未完のコード断片あり）。具体的な SQL やロジックは未完成。
- position_sizing の価格取得が欠損（0.0）の場合、現状では exposure が過小評価される可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討予定。
- ログディレクトリ作成やプロセス優先度設定は権限によって失敗する可能性があり、失敗時は警告を出して安全にスキップする設計。
- monitoring の使用中は監視データが本番 sqlite_path を参照するため、テスト時は注意（paper_trading 環境でも監視 DB は本番パスを使用する実装）。
- config/*.yaml の内容検証は PyYAML が存在する場合のみ行われる（インストールされていない場合は警告してスキップ）。

### 参考: 主な環境変数（デフォルト値）
- KABUSYS_ENV: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- MONITOR_POLL_INTERVAL: 60（秒）
- LOG_DIR: logs/
- LOG_LEVEL: INFO
- KILL_FLAG_CLEAR_ON_START: 0

---

今後の予定（ToDo / 次のリリース候補）
- factor_research の完全実装（DuckDB SQL/ロジックの追加）。
- execution の各コンポーネント（ExecutionEngine, BrokerClient 実装）の詳細レビューと追加テスト。
- 単体テスト・統合テストの拡充（設定読み込み、ウィザード、検証ツール、position sizing 等）。
- ドキュメントの充実（PortfolioConstruction.md 参照箇所の実体化、使用例 / API リファレンス）。

もし特に強調したい項目や、より詳細な変更履歴（ファイル毎の差分に基づく行単位の記述など）が必要であれば教えてください。