# Changelog

すべての重要な変更はこのファイルで記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な注記:
- このリリースはソースコードの初期機能群をまとめた初版リリース相当の内容を反映しています（パッケージ内部の __version__ は 0.1.0）。
- SQLite / DuckDB を組み合わせたローカル DB を利用する設計です。環境変数や .env による設定を基本とします。

## [0.1.0] - 2026-04-18

### Added
- 基本インフラ・ユーティリティ
  - 環境変数 / .env 読み込み・管理モジュール (kabusys.config)
    - プロジェクトルート検出ロジック（.git / pyproject.toml を基準）により CWD に依存しない自動 .env ロードを実装。
    - 必須環境変数取得ヘルパー `_require()`、環境切替用プロパティ (is_live / is_paper / is_dev) を提供。
    - データベースパス、PID/kill フラグ、監視閾値などの設定プロパティを実装。
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject）を追加。

  - ロギング設定ユーティリティ (kabusys.utils.logging_setup)
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR の自動作成とフォールバック（作成失敗時はコンソール出力のみ）を実装。
    - ログレベルの解決順（引数 > 環境変数 > デフォルト）を実装。

  - プロセス優先度/CPU affinity ユーティリティ (kabusys.utils.process_priority)
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority。
    - 指定コア数へプロセスを固定する set_cpu_affinity。権限不足や未対応 OS の場合は警告を出してスキップ。

- 実行用スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する挙動を実装。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止用フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱いを実装。
    - RiskManager にデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() から取得。

  - 監視（Monitoring）起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のインスタンスを生成し、ポーリングループで定期チェックを実行。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は実行環境に関わらず本番 sqlite_path を使用する挙動をドキュメント化。

- 設定関連 CLI
  - 対話式設定ウィザード (kabusys.config_setup)
    - .env の初期作成 / 更新支援。J-Quants トークンや Kabu API パスワードなどの必須項目を対話的に入力。
    - 生成/更新された .env をファイルに保存するユーティリティを提供。
    - デフォルト項目、選択肢、シークレットマスク表示などのユーザーフレンドリな入出力を実装。

  - 設定検証 CLI (kabusys.validate_config)
    - .env と config/*.yaml の妥当性チェックを実行。
    - 必須環境変数の未設定検出、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の値検査、DB パスの親ディレクトリチェック、YAML パース検証（PyYAML が利用可能な場合）などを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - 銘柄選定と重み計算 (portfolio_builder)
    - select_candidates: スコア降順、signal_rank によるタイブレークで候補を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコア合計がゼロの場合は等配分にフォールバックし警告を出す。

  - リスク調整 (risk_adjustment)
    - apply_sector_cap: セクターごとの既存保有比率を評価し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告の上 1.0 でフォールバック。

  - 取付け・株数算出 (position_sizing)
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した株数計算を実装。
    - 単元（lot_size）での丸め、1 銘柄上限、aggregate cap によるスケーリング、残余キャッシュに基づく再配分ロジックを実装。
    - cost_buffer を考慮した保守的なコスト見積りを実装。

- 研究・分析ツール
  - ファクター研究モジュール (kabusys.research.factor_research)
    - Momentum 等のファクター計算機能（設計方針、定数、calc_momentum 関数の骨格）を追加。DuckDB の prices_daily を参照して計算する設計。

- ツール
  - Paper Trading 検証レポート生成スクリプト (kabusys.tools.paper_verification_report)
    - paper_trading DB（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションで期間・DB パスを指定可能。

### Changed
- （初版のため該当なし）内部実装と API は今後のリリースで細かく変更される可能性があります。

### Fixed
- （初版のため該当なし）

### Security
- 環境変数ファイル .env は生成時に明確に「Git にコミットしない」旨の注意を .env ヘッダに追加。機密情報は .env に保存することを想定。

## 重要なマイグレーション / 運用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。未設定時は各所で ValueError を送出します。
- 環境切替:
  - KABUSYS_ENV = development | paper_trading | live をサポート。paper_trading は本番 DB と分離され、paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
- デフォルト DB/ログパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log（ログディレクトリ作成に失敗した場合はコンソールのみ）
- 監視/実行停止:
  - 停止フラグファイル: data/stop_requested.flag をプロジェクトルートに置くことで run_monitoring / run_execution が検知して停止します。
  - 実行エンジンの PID ファイル: data/execution.pid（run_execution で使用）。
- MONITOR_POLL_INTERVAL:
  - 監視ループの間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。不正な値や 0 以下は無視されデフォルト 60 秒が使われます。
- PAPER_FILL_MODE:
  - Paper Trading の fill 動作は環境変数 PAPER_FILL_MODE（instant/partial/never/reject）で制御可能。無効値は例外を発生させます。
- KILL_FLAG_CLEAR_ON_START:
  - 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START=1 の設定は危険である旨の警告を出します。デフォルトは 0（クリアしない）。

## 利用可能な CLI / モジュール一覧（抜粋）
- 起動スクリプト
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- 設定 / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ライブラリ API
  - kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - kabusys.research.factor_research: ファクター計算機能（DuckDB 接続を受け取る設計）

---

今後のリリースでは以下を予定しています（非網羅）:
- factor_research の完全実装（Momentum / Volatility / Value / Liquidity 等の計算）
- ExecutionEngine 周りの耐障害性向上と各コンポーネント（OrderManager / Reconciler / RiskManager）の詳細実装ドキュメント化
- 単体テスト・統合テストの追加
- 銘柄ごとの lot_size や価格フォールバック処理などの拡張

ご不明点や追記してほしい項目があればお知らせください。