# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョンはコードベース内の __version__ を基にしています。

## [Unreleased]
（現状なし）

## [0.1.0] - 2026-04-18
初期リリース。自動売買システム KabuSys の基本機能群を実装しました。以下はコードベースから推測してまとめた主要な追加点・設計上の特徴です。

### 追加 (Added)
- 全体
  - パッケージ初期版を公開（__version__ = 0.1.0）。
  - DuckDB / SQLite を用いたデータ処理基盤を採用（設定可能なパス）。
  - ログ設定・プロセス制御・環境設定補助など、運用に必要なユーティリティ群を実装。

- 環境設定 / 起動支援
  - .env ファイル自動ロード機能を実装（プロジェクトルート検出：.git / pyproject.toml 基準）。
  - 複雑な .env パースロジックを実装：
    - export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし行のインラインコメント扱いルール（'#' の前に空白がある場合のみコメント扱い）。
  - Settings クラスを実装し、環境変数から各種設定値をプロパティとして提供：
    - J-Quants / kabuステーション / LINE API トークン等。
    - データベースパス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH）と監視設定（pid/kill フラグ等）。
    - Paper Trading 用の fill モード（instant/partial/never/reject）検証。
    - 環境（development / paper_trading / live）・ログレベル等の検証。
  - 対話式の環境設定ウィザード CLI (config_setup.py) を追加：
    - .env 作成・更新を支援。秘密値は表示マスク。
    - 保存テンプレートと注意コメントを含む .env 出力。
  - 設定検証 CLI (validate_config.py) を追加：
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と（PyYAML がある場合）パース検証。
    - 本番環境向けのガード（LINE 通知、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス管理
  - 統一的なログ設定ユーティリティを実装 (utils.logging_setup.setup_logging)：
    - stdout 出力（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの決定順序（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティを実装 (utils.process_priority)：
    - Windows と POSIX 系（Linux, macOS, FreeBSD）に対応する優先度設定（high/normal/low）と CPU コア制限機能。
    - 権限不足や未対応 OS 時は安全にフォールバックして警告を出力。

- 実行 / 監視起動スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV により paper_trading と live を分離。
    - paper_trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いて実行環境に応じたブローカークライアントを生成（MockBrokerClient を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ検知で安全に停止。
    - 実行前に監視テーブルを冪等に初期化（init_monitoring_db）。
  - run_monitoring.py:
    - SystemMonitor 起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関係なく本番 sqlite_path を使用（監視データは本番 DB を参照）。
    - 停止フラグ検知・例外捕捉・プロセス優先度設定などの運用ロジックを実装。

- ポートフォリオ構築（Portfolio）
  - portfolio.portfolio_builder:
    - 候補選定（select_candidates）: score 降順、同点は signal_rank でタイブレーク。
    - 重み計算: 等配分（calc_equal_weights）とスコア加重（calc_score_weights）。全銘柄スコアが 0 の場合は等配分へフォールバック（警告出力）。
  - portfolio.risk_adjustment:
    - セクター集中制限（apply_sector_cap）: 既存保有を基にセクター上限（max_sector_pct）を超える場合に同セクターの新規候補を除外。unknown セクターは上限適用除外。
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に応じた投下資金乗数を返す（未知レジームは警告と 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数計算。
    - risk_based: 損切り率や risk_pct を使ったポジションサイズ算出、lot_size（単元）で丸め。
    - equal/score: 重みと max_utilization を考慮した配分、1 銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を使った保守的推定、残差処理によるロット単位での再配分を実装。

- 分析 / 検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、P95 レイテンシ等を集計。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL を判定。
    - --from / --to / --db オプションをサポート。

- 研究用（Research）
  - research.factor_research（ファクター計算モジュール）を追加（モメンタム等の計算を実装予定、DuckDB 接続に基づく設計）。（注: ファイルの末尾が途中で切れているため一部未完）

### 変更 (Changed)
- N/A（初期リリースのため履歴ベースの変更はなし）

### 修正 (Fixed)
- N/A（初期リリースのためバグ修正履歴はなし）

### 注意点 / 運用上の説明
- .env は機密情報が含まれるため絶対にコミットしないよう README 等で明示する旨が config_setup.py に注記されています。
- run_monitoring は環境にかかわらず本番の sqlite_path を使用する設計のため、監視データと paper_trading データは分離していることを理解して運用してください。
- process priority / cpu affinity の設定は権限が必要な場合があり、失敗した場合は警告ログを出して安全にスキップします。
- PAPER_FILL_MODE の値は厳密に検証され、無効値であれば起動時に例外を発生させます。
- config/*.yaml の検証は PyYAML がインストールされている場合にのみパース検証を行います（未インストールなら警告）。

### 既知の未完事項（今後の改善候補）
- research.factor_research モジュールがファイル末尾で切れており、実装が未完に見える箇所があります（補完・テストが必要）。
- position_sizing の price 欠損時の取り扱い（TODO コメントにあるフォールバック価格ロジック）が未実装。
- 将来的な拡張として銘柄別の lot_size（単元）対応や、より詳細なブローカー/市場シミュレーションの拡張が想定される。

---

上記はソースコードの実装とコメントから推測してまとめた CHANGELOG です。必要であれば、ファイル毎により詳細な変更点（関数単位の説明やサンプル設定値）を追記できます。どの形式／粒度がよいか指示ください。