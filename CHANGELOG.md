# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン: 0.1.0 — 初回リリース。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-20
初回リリース。日本株自動売買システム KabuSys の基礎機能を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 実行・監視用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（settings.paper_sqlite_path を使用）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動制御（threaded）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルを初期化。

- 設定管理
  - config.py
    - .env の自動ロード（プロジェクトルートを .git / pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - Settings クラス: 各種環境変数アクセスをプロパティで提供（J-Quants、kabu API、DB パス、監視閾値、環境種別など）。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等ペーパートレード用の設定を追加。
  - config_setup.py
    - インタラクティブな .env 設定ウィザードを追加（.env の作成・更新を支援）。
    - デフォルト値やシークレット入力、確認・保存フローを実装。

- 設定検証 CLI
  - validate_config.py
    - .env / config/*.yaml の起動前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・YAML ファイル存在チェック。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR / app_name に基づく設定、既存ハンドラのクリア処理等を実装。
  - utils/process_priority.py
    - psutil を使ったプロセス優先度設定（Windows / POSIX を吸収）。
    - set_cpu_affinity による CPU affinity 固定機能を追加。
    - 権限不足等の状況では警告ログでスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルのスコア降順で候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算。スコア全0時のフォールバックを実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有比率に基づく候補除外）。
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時スケーリング）、cost_buffer による保守的見積り、残余キャッシュを使った再配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）から集計レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）など。
    - Pass/Fail 判定の閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
    - --from / --to / --db オプションをサポート。

- データベース統合
  - SQLite（監視・注文履歴）と DuckDB（分析用）を両方利用する設計を採用。
  - monitoring_db.init_monitoring_db を起動前に呼び出して監視テーブルの存在を保証（冪等）。

- 研究・ファクター計算（開始）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity の設計と初期実装（モメンタム計算関数など、DuckDB の prices_daily/raw_financials を使う方針）。
    - 設計ドキュメント参照の記載と計算用定数を実装（ただしファイル末尾は未完の箇所あり）。

- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。

### 変更 (Changed)
- （初回リリースにつき過去からの変更はなし）

### 修正 (Fixed)
- （初回リリースにつき修正履歴はなし）

### セキュリティ (Security)
- 機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env にて管理する設計。
- config_setup の注意書きで .env を Git にコミットしないことを明記。

### 既知の制限・注意点 (Notes & Known Issues)
- research/factor_research.py は一部未完成（ファイル末尾に未完のコードあり）。研究用モジュールは今後の拡張を予定。
- position_sizing の価格フォールバック: price が欠損（0.0）の場合、エクスポージャーが過小見積もられる可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバックを導入予定。
- process_priority / set_cpu_affinity はプラットフォームや権限に依存するため、権限不足時は実行をスキップする設計（警告ログ）。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する。

### 利用開始手順（概要）
1. .env を作成（`python -m kabusys.config_setup` を推奨）
2. 設定検証（`python -m kabusys.validate_config`）
3. 実行：監視 `python -m kabusys.run_monitoring` / エンジン `python -m kabusys.run_execution`
4. ペーパートレード検証レポート: `python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD`

---

今後の予定: 研究モジュールの完成、戦略本体（シグナル生成・Engine の実装詳細拡充）、テストカバレッジの追加、監視/アラート強化、単元ごとの lot_size を銘柄別に扱う拡張など。