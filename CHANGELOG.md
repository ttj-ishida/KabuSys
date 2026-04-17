# Changelog

すべての重要な変更はこのファイルに記録します。

このプロジェクトは Keep a Changelog の慣習に従います。  
安定版リリースでは日付を付与します。

※ 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- 今後の予定事項・改善案（例）
  - research.factor_research のボラティリティ計算完了・追加テスト
  - ExecutionEngine / Reconciler 周りの統合テスト強化
  - 銘柄ごとの lot_size を stocks マスターから取得する拡張
  - ドキュメント・CLI ヘルプの充実化

---

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システムの基礎モジュール群を追加。

### Added
- 基本パッケージとバージョン
  - パッケージ __version__ を "0.1.0" に設定（src/kabusys/__init__.py）。

- 環境・設定管理
  - Settings クラス（src/kabusys/config.py）を追加し、環境変数経由で各種設定（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、監視閾値、Paper Trading の設定など）を取得する API を提供。
  - .env 自動ロード機能を実装：
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込む。
    - OS 環境変数を保護する protected 上書き挙動、KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化が可能。
  - .env 解析の堅牢化：
    - export プレフィックス対応、クォート値とバックスラッシュエスケープ対応、行中コメントの取り扱いなど。

- CLI ツール
  - 設定ウィザード: python -m kabusys.config_setup
    - 対話式に .env を作成・更新するウィザード（既存値表示・シークレットマスク・保存確認）。
  - 設定検証: python -m kabusys.validate_config
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース検証（PyYAML がない場合は警告）を実行。
    - --strict オプションで警告を失敗扱いにできる。
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
    - paper_trading 用 SQLite（デフォルト data/paper_trading.db）から検証指標を集計しレポートを出力。
    - 指標: 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）など。
    - 既定の閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- 実行 / 監視ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てを行う。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止制御。
    - RiskManager に対するデフォルト RiskConfig（max_position_pct=0.20 等）をセット。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。0 以下は無効としてデフォルトにフォールバック。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視 DB を初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - プロセス起動時にプロセス優先度を "high" に設定。

- ポートフォリオ構築およびポジション計算
  - 銘柄選定 / 重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等分配へフォールバックし警告を出力。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づき、新規候補を除外（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは 1.0 にフォールバック（警告）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割当方法をサポート。
    - 単元株（lot_size）による丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によりスケールダウン処理を実装。
    - cost_buffer を考慮した保守的コスト見積りと、小数端数（fractional remainder）に基づく追加配分ロジックを実装。
    - 価格欠損時のスキップやログ出力など堅牢化。

- リサーチ（ファクター算出）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - Volatility（途中実装まで確認）: ATR、相対 ATR、20日平均売買代金、出来高比率等を計算するための骨組みを追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定を提供。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスをピン留め。無効な値や権限不足は警告でスキップ。

- パッケージ初期化
  - portfolio モジュールをトップレベルで再エクスポート（src/kabusys/portfolio/__init__.py）。
  - tools パッケージの追加（tools/__init__.py）。

### Changed
- （初回リリースにつき変更履歴はなし）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Notes / Behavior
- DB 関連
  - duckdb: 分析用（duckdb_path）
  - sqlite: 監視・発注履歴用（SQLITE_PATH）。Paper Trading 時は PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離。
- セキュリティ
  - .env は生成時に Git へコミットしないよう注意喚起を出力。
  - シークレット項目は config_setup のプレビューでマスク表示。
- 実行上の注意
  - run_monitoring / run_execution は停止フラグファイルを監視して安全に停止できる仕組みを備える。
  - process priority / affinity の設定は OS 権限に依存し、失敗した場合は警告ログに留めます。

---

今後の改善候補（参考）
- research.factor_research の残り部分（ボラティリティ・流動性計算）の完成とユニットテスト追加
- Strategy / Execution の統合テストスイート（モックブローカー含む）
- 銘柄別 lot_size のサポート、手数料・スリッページモデルの強化
- config の型チェック・schema バリデーション強化（YAML スキーマ等）

--- 

（以上）