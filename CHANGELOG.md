# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
日付はこのコードスナップショット作成日（2026-04-18）を使用しています。

## [0.1.0] - 2026-04-18

### 追加
- 全体
  - 初期リリース。パッケージメタ情報に __version__ = "0.1.0" を追加。
- 実行スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視プロセス起動時にプロセス優先度を "high" に設定。
    - 監視は環境（KABUSYS_ENV）に関わらず production 用の sqlite_path を使用する仕様を明示。
    - 停止フラグ（data/stop_requested.flag）を検出してループを終了。
  - run_execution.py を追加
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を採用（mock と実ブローカーを切替可能）。
    - ExecutionEngine を別スレッドで実行、停止フラグ検出で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境
  - config.py を追加
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。`.env` と `.env.local` の読み込み順・上書きルールを明確化。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パースは引用符・エスケープ・インラインコメント等に対応。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境種別判定など）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE の妥当性検査、KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py を追加
    - 対話式 .env ウィザードで .env の初期作成・更新を支援。既存値の再利用、シークレット項目のマスク表示などに対応。
  - validate_config.py を追加
    - 起動前の設定検証 CLI を追加（必須環境変数・KABUSYS_ENV・ログレベル・DB パスの親ディレクトリ・config/*.yaml の存在とパース検証、live モード用ガード等）。
    - --strict オプションで警告を FAIL 扱いにするモードを提供。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py を追加
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティ。
    - ログレベル・ログディレクトリの解決ルールを明記、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py を追加
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定する関数 set_process_priority(level) を提供。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加（指定なしなら何もしない）。
    - 権限不足や未対応 OS では警告を出して安全にスキップする設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py を追加
    - select_candidates(): スコア降順で候補抽出（タイブレークは signal_rank）。
    - calc_equal_weights(), calc_score_weights(): 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py を追加
    - apply_sector_cap(): セクター集中制限を適用し、上限超過セクターの候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier(): 市場レジームに応じた資金乗数（bull/neutral/bear）を返す。未知レジームは警告を出し 1.0 にフォールバック。
  - portfolio/position_sizing.py を追加
    - calc_position_sizes(): allocation_method ("risk_based" / "equal" / "score") に基づく発注株数決定。単元株（lot_size）丸め、単銘柄上限・aggregate cap（利用可能現金）を考慮したスケーリング、コストバッファ考慮、残差配分ロジックを実装。
  - portfolio/__init__.py を追加して主要関数をエクスポート。
- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用検証レポート生成 CLI を追加。P95 計算、稼働率・注文成功率・送信率・レイテンシ指標の取得と基準値比較（デフォルト閾値をソース内で定義）。
    - DB パスは --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト の順で解決。
    - 日付フィルタは引数 --from / --to を受け取り ISO8601 UTC フォーマットで内部クエリに適用。
- リサーチ
  - research/factor_research.py を追加（初期スケルトン）
    - Momentum、Value、Volatility、Liquidity などのファクター計算方針を定義。DuckDB の prices_daily / raw_financials を利用する設計で、関数 calc_momentum の実装が開始（ファイル末尾はスニペットで切れている）。

### 変更
- 監視と実行の DB 接続ポリシーを明確化
  - run_monitoring: 監視は環境に関係なく settings.sqlite_path（本番監視 DB）を使用する設計に。意図的に監視 DB の分離を行わない仕様。
  - run_execution: paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離する挙動を導入。
- ロギング設定の既定値
  - 日次ローテーションで 30 日分のログを保持するように設定（TimedRotatingFileHandler, backupCount=30）。
  - コンソール出力は stdout を利用（cron 等で stdout/stderr を一本化する運用を想定）。

### 修正（防御的実装）
- 環境変数パースの堅牢化
  - config._parse_env_line(): シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理、export プレフィックス対応などを実装し .env のさまざまな記法に耐性を持たせた。
- run_monitoring._get_poll_interval(): MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）の場合はデフォルト 60 秒にフォールバックして警告を出すように変更。
- utils/logging_setup.py: ログディレクトリ作成失敗時にファイルハンドラだけをスキップして、コンソール出力は継続するフェイルセーフを追加。
- utils/process_priority.py: 未対応 OS や権限不足で例外が発生した場合は警告でスキップし、起動を阻害しないように修正。

### 注意事項（Breaking / Important）
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用する」仕様です。テスト / 開発環境で監視 DB を分離したい場合は設定を見直してください。
- config.py の自動 .env 読み込みはデフォルトで有効です。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など設定値は妥当性チェックが入り、不正な値だと ValueError を発生させます。起動前に validate_config で検証することを推奨します。

### 既知の未実装 / 今後の課題
- research/factor_research.calc_momentum の実装が途中（スニペットが末尾で切れています）。他のファクター計算（Value/Volatility/Liquidity）も同様に実装予定。
- position_sizing の lot_size を銘柄別にする拡張（stocks マスタの導入）を TODO に記載。
- price が欠損（0.0）の場合のフォールバック価格ロジック（前日終値や取得原価の利用）は未実装のため精度低下の可能性あり（risk_adjustment.apply_sector_cap 内コメント参照）。

---

このリリースではシステム運用（監視・実行）周りの起動スクリプト、設定管理 CLI、ログ／プロセスユーティリティ、ポートフォリオ構築の純粋関数群、Paper Trading 検証ツールなど、運用とアルゴリズム双方の基盤実装が導入されました。ユーザ側はまず .env を作成（config_setup）し、python -m kabusys.validate_config で設定検証後、run_execution/run_monitoring を起動してください。