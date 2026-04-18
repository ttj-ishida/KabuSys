# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

次のバージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-18

Added
- 初回リリース。KabuSys のコア機能群を実装・追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - RiskManager, OrderManager, Reconciler, OrderRepository を組み立てて ExecutionEngine を起動。エンジンは別スレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - _EXECUTION_PID（data/execution.pid）へ PID 情報を出力する想定。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告ログを出してデフォルトを使用。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する（監視は本番 DB を参照する設計）。
    - data/stop_requested.flag による停止検知、KeyboardInterrupt のハンドリング、コネクションのクローズ処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - src/kabusys/config.py
    - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パースロジック（_parse_env_line）で export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメントなどに対応。
    - Settings クラスを提供。多くのプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE のバリデーション等）を通じて環境変数を型安全に取得可能。
    - KABUSYS_ENV / LOG_LEVEL 等の妥当性検証を行い、無効値は例外を投げる。

  - src/kabusys/config_setup.py
    - .env 初期作成・更新の対話式ウィザードを実装。既存 .env の読み込み・再利用、シークレット値のマスク表示、保存確認をサポート。
    - 書き出しフォーマットはコメント付きで .env を生成（Git にコミットしない旨を明記）。

  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース検証（PyYAML インストール有無によりスキップ可能）、KABUSYS_ENV=live 時の追加警告等を実行。
    - --strict フラグで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates: スコア降順、signal_rank でタイブレーク）。
    - ウェイト計算（calc_equal_weights、calc_score_weights）。スコアが全て 0 の場合は等分配へフォールバック（警告ログ）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）。既存保有のセクター比率に基づき新規候補を除外。unknown セクターは上限適用除外。
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を適用。cost_buffer（スリッページ・手数料見積）により保守的にコストを見積もり、合計が available_cash を超える場合はスケーリングと再配分（残差処理）を行う。
    - 価格欠損時のスキップやログ出力を実装。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通ログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR の解決順、ログディレクトリ作成失敗時のフォールバック等に対応。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを実装。Windows と POSIX 系（Linux, Darwin, FreeBSD）を吸収し、例外時は警告を出してスキップ。

- モニタリング用 DB 初期化（init_monitoring_db）や SystemMonitor の利用（run_monitoring/run_execution で呼び出し）を想定したインターフェースを実装（具体実装は monitoring パッケージ内）。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、レイテンシ（avg/max/P95）等を集計し、閾値（稼働率 99%、fill 90%、send 95%、P95 <= 200ms）と比較して PASS/FAIL を判定。
    - 日付範囲フィルタ（--from / --to）と DB パス指定（--db または環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - P95 計算、欠損データ時の N/A 表示や sqlite テーブル存在チェックに対する堅牢なハンドリングを実装。

- リサーチ
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの骨組みを追加。Momentum / Value / Volatility / Liquidity の計算方針と定数を定義。DuckDB 接続経由で prices_daily / raw_financials を参照する設計。calc_momentum の実装が始まっている（途中まで）。

Changed
- 初期リリースのため履歴は追加のみ。

Fixed
- 初回リリースのため特定のバグ修正履歴は無し。

Notes / 注意事項
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダにも注記あり）。
- run_monitoring は監視用 DB に production の sqlite_path を使う設計です。監視用途で別 DB を使いたい場合は環境変数および設定の見直しが必要です。
- process_priority や CPU affinity の設定は OS 権限に依存します。権限不足で設定に失敗した場合は警告が出力され動作は継続しますが期待通りの優先度にならないことがあります。
- paper_verification_report の閾値は現状ハードコードされています。プロダクション利用時は必要に応じて閾値や集計ロジックを調整してください。
- research/factor_research.py は実装完了前の状態（calc_momentum が途中）です。ファクター計算を完全に使うには追加実装が必要です。

照会先
- ソースコード: src/kabusys 以下の各モジュール参照
- バージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）