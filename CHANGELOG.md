# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測した機能追加・挙動・注意点を記載したものであり、実装上の注釈や既知のフォールバック動作も含みます。

## [0.1.0] - 2026-04-19
初回リリース。本リリースでは自動売買システム「KabuSys」のコア機能群（設定管理、実行/監視ランナー、ポートフォリオ構築、ポジションサイジング、ユーティリティ、検証ツール等）をまとめて追加しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ保存・分析基盤を採用（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。

- 設定・起動関連
  - 環境変数管理モジュールを追加（kabusys.config）。
    - プロジェクトルートを .git / pyproject.toml から自動検出して .env 自動読み込み（.env → .env.local、OS環境変数優先）。
    - .env のパースはクォート、エスケープ、コメント、`export KEY=val` 形式に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値 等をプロパティで取得可能。
    - PAPER_FILL_MODE/PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定を追加。
  - 環境設定ウィザード CLI を追加（kabusys.config_setup）。
    - 対話形式で .env を作成・更新。シークレットのマスク表示、選択肢提示、保存確認を実装。
    - デフォルト値、選択肢、説明付き。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DBパス・config YAML 存在チェック、KABUSYS_ENV=live 時の追加ガード等を実施。
    - --strict オプションで警告を失敗扱いにできる。

- 実行 / 監視ランナー
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成を利用（paper_trading 時は MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - data/execution.pid を pid_file として利用、data/stop_requested.flag による安全停止をサポート。
    - RiskManager のデフォルト設定（max_position_pct=0.20 等）を埋め込みで提供。
  - 監視ポーリングループ起動スクリプトを追加（kabusys.run_monitoring）。
    - 環境にかかわらず監視は本番の sqlite_path を使用する設計。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。0以下や不正値はデフォルトへフォールバック。
    - 停止フラグファイルの検知でループ停止、KeyboardInterrupt による終了ハンドリング。

- ポートフォリオ構築・リスク調整・ポジションサイズ
  - ポートフォリオ選定と重み付け（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順 + signal_rank によるタイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights を実装。全スコアが 0 の場合は等金額配分にフォールバックして警告を出力。
  - セクター上限適用・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有に基づきセクター集中を検出し、上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム ("bull", "neutral", "bear") に対する投下資金乗数を提供。未知のレジームは 1.0 でフォールバックし警告を出す。
  - ポジションサイズ計算（kabusys.portfolio.position_sizing）
    - risk_based / equal / score の allocation_method に対応した株数計算を実装。
    - 単元株（lot_size）で丸め、1 銘柄上限・アグリゲート上限（available_cash）を尊重。
    - cost_buffer による手数料/スリッページの保守的見積を採用。必要に応じてスケーリングと残差処理を行い再配分。
    - 価格欠損や負値価格を検出してスキップする安全設計。

- ユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - LOG_DIR / LOG_LEVEL 解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみとする。
    - stdout を使用する理由（Task Scheduler/cron での一本化）を明記。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - psutil を用いた cross-platform 優先度設定（Windows: HIGH_PRIORITY_CLASS 等, POSIX: nice 値）。
    - set_cpu_affinity で最初の N コアにピン留めする機能（利用可能なコア数より大きい指定は全コア使用）。
    - 権限不足や未対応 OS は警告して安全にスキップ。

- 検証・レポートツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
    - SQLite (paper_trading.db) を読み込んで稼働率 (uptime)、注文成功率、送信率、P95 レイテンシ等を集計。
    - P95 算出、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
    - コマンドライン引数 --from / --to / --db をサポート。

- リサーチ
  - ファクター計算の枠組みを追加（kabusys.research.factor_research）
    - モメンタム / MA200 / ATR / ボリューム等の計算方針と定数を実装（calc_momentum の枠組み開始、定数定義）。
    - DuckDB 接続を受け prices_daily / raw_financials テーブルに基づく設計。

### 変更 (Changed)
- ログ出力
  - デフォルトで stdout にログを出力するように設計。ファイルハンドラはログディレクトリ作成成功時のみ有効化される。
- DB パスの扱い
  - run_execution は paper_trading 環境で専用 SQLite を使用する（data/paper_trading.db デフォルト）ことで本番データと分離。
  - run_monitoring は監視用 DB に常に本番 sqlite_path を使用する設計（環境に依存せず監視データを統合する意図）。

### 修正 / 考慮 (Fixed / Notable behavior)
- 環境変数パースの堅牢化
  - .env パーサはシングル/ダブルクォートとエスケープに対応し、インラインコメント処理を改善。
  - キーが空の行や無効行は無視。
- フォールバックと安全策
  - MONITOR_POLL_INTERVAL の不正値は警告してデフォルト 60 秒にフォールバック。
  - process_priority の設定が権限不足や未対応 OS で失敗してもログ警告を出して処理を継続。
  - logging_setup はログディレクトリ作成に失敗しても例外を投げずコンソール出力で継続。
  - position_sizing は価格欠損や 0/負価格を検出してスキップ、アグリゲート超過時はスケールダウンして lot 単位で再配分するロジックを導入。

### ドキュメント / 使用上の注意 (Documentation / Notes)
- CLI / スクリプト
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 重要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD （必須）
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 向け）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - SQLITE_PATH / DUCKDB_PATH（デフォルト: data/monitoring.db, data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（本番で 1 を設定すると自動クリアされるため危険。デフォルト 0 推奨）
- Live 環境注意
  - validate_config は KABUSYS_ENV=live の場合に LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START=1 を警告します。実運用前に必ず検証してください。
- 未実装 / TODO
  - research.factor_research の calc_momentum 等は枠組みを実装中（ファイル末尾が未完の状態）。完全な指標計算ロジックの追加が必要。
  - position_sizing の価格フォールバック（前日終値や取得原価等）が TODO コメントとして残っています。
  - 将来的な拡張: 銘柄ごとの lot_size を stocks マスタに持たせる設計（現状は全銘柄共通 lot_size）。

### セキュリティ (Security)
- .env ファイルは絶対にリポジトリにコミットしない旨を config_setup のヘッダに追記。
- シークレットは config_setup の対話でマスク表示され、ファイルへは平文で保存される点に注意（ファイル保護を推奨）。

---

今後のリリースでは以下を想定しています:
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity 指標の算出）
- ExecutionEngine / BrokerClient の単体テスト整備と Mock の強化
- config ファイル（config/*.yaml）に対するより詳細な構成検証とスキーマの導入
- 銘柄別 lot_size 対応や取引コスト推定の高度化

ご要望があれば、CHANGELOG をリポジトリの実際のコミット履歴に合わせてより詳細に分割（追加されたファイルごと、コミット単位）して作成します。