# Changelog

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」の形式に従います。セマンティックバージョニングを採用しています。

## [Unreleased]

（現時点は未リリースの変更はありません）

---

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しています。

### 追加 (Added)
- 基本パッケージ構成を追加
  - kabusys パッケージ本体とサブモジュール群（portfolio、execution、monitoring、tools、utils、research 等）を実装。
  - パッケージバージョンは __version__ = "0.1.0"。

- 設定管理（config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env のパース実装（コメント、export 形式、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスで各種設定（J-Quants / kabuAPI / DB パス / PaperTrading モードなど）をプロパティとして提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。

- 環境設定ウィザード CLI（config_setup）
  - 対話式に .env を作成・更新するウィザード。
  - 必須/任意項目、シークレットマスキング、デフォルト値、選択肢表示などをサポート。
  - .env を安全なテンプレート形式で出力。

- 設定検証 CLI（validate_config）
  - 起動前に .env と config/*.yaml を検証するユーティリティ。
  - 必須環境変数のチェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリチェック、config YAML の存在・パースチェック（PyYAML がある場合のみ）を実行。
  - --strict モードで警告をエラー扱いにできる。

- 実行エンジン起動スクリプト（run_execution）
  - ExecutionEngine 起動スクリプトを提供。
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH をサポート）。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
  - 実行プロセス用 PID ファイルサポート、停止フラグ（data/stop_requested.flag）検出で安全に停止する仕組み。
  - RiskManager の設定（max_position_pct、max_utilization、rate_limit 等）と初期ポートフォリオ値を broker.get_available_cash() から取得して初期化。

- 監視ループ起動スクリプト（run_monitoring）
  - SystemMonitor を一定間隔で実行するポーリングループ。
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告後デフォルトにフォールバック。
  - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
  - 停止フラグ検出によるループ終了、KeyboardInterrupt による終了処理、DB 接続の確実なクローズを実装。

- ロギング設定ユーティリティ（utils.logging_setup）
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を root ロガーに設定。
  - LOG_DIR / LOG_LEVEL による上書き、既存ハンドラのクリーンアップ、ログローテーションで 30 日分保持。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。

- プロセス優先度・CPU affinity ユーティリティ（utils.process_priority）
  - Windows / POSIX を吸収してプロセス優先度を "high" / "normal" / "low" で設定。
  - CPU affinity を最初の N コアに制限する機能を提供（psutil 利用、許可エラーは警告で無視）。

- ポートフォリオ構築ライブラリ（portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率に応じた配分。全銘柄スコアが 0 の場合は等配分にフォールバック（WARNING）。
  - risk_adjustment
    - apply_sector_cap: セクター集中の上限チェック。既存ポジションのセクター別時価を計算し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却。未知のレジームは 1.0 でフォールバック（WARNING）。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer 等を考慮。
    - aggregate cap（available_cash）超過時はスケーリングし、lot_size 単位で残余配分を行う実装。

- Paper Trading 検証レポートツール（tools.paper_verification_report）
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計してレポートを出力。
  - 集計指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等。
  - 通常の閾値による PASS/FAIL 判定を実装（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms など）。
  - 日付フィルタ（--from / --to）、DB パス上書き（--db）をサポート。
  - データ不足やテーブル未存在時のフォールバックを考慮。

- research/factor_research（骨格実装）
  - DuckDB 接続を受け取り prices_daily / raw_financials テーブルからファクターを計算するための設計・定義（モメンタム / Value / Volatility / Liquidity）。（実装は一部切れ目あり、設計に基づいた関数群を配置）

### 変更 (Changed)
- （初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- （初回リリースのため修正履歴はありません）

### 既知の制約・注意点
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。
- Paper Trading 用 DB と本番用 DB は意図的に分離されているが、開発者は環境変数を確認して正しい DB を指定する必要がある。
- position_sizing 等で価格が欠損（0.0）だった場合、現在はスキップ処理になっているため保守的な見積りに注意（TODO コメントあり）。
- 一部モジュール（SystemMonitor、monitoring_db、ExecutionEngine 等）の詳細実装は本リリースに依存しているが、ここで提供された起動スクリプトはそれらと連携するよう設計されている。

### セキュリティ (Security)
- 本リリースではセキュリティに関する明示的な修正はありません。機密情報（API トークン/パスワード）は .env に保管し、.env をリポジトリにコミットしない旨をドキュメント化しています。

---

今後の予定:
- research/factor_research の完全実装、テスト追加、ドキュメント強化。
- 監視・実行コンポーネントの統合テスト、エラーハンドリングの強化。
- 銘柄別単元株情報のサポート、手数料/スリッページの詳細モデリング。