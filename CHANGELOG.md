# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

注: このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージメタ情報: kabusys の初期バージョン __version__ = "0.1.0" を定義。
- 起動スクリプト / ランタイム
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、専用のペーパートレード用 SQLite（data/paper_trading.db 既定）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立てて ExecutionEngine をスレッドで実行。
    - data/stop_requested.flag を監視して安全に停止。起動中の PID を data/execution.pid に記録する仕組みを想定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - stop フラグファイルを検知すると監視ループを終了。
- 設定・環境変数管理
  - config.py
    - Settings クラスによる環境変数ラッパーを提供（J-Quants, kabu API, DB パス, モニタ閾値等を取得）。
    - .env 自動読み込み機構（プロジェクトルート判定: .git または pyproject.toml を探索。OS 環境変数を保護しつつ .env / .env.local を読み込む）。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の値検証、各種パスの Path 型化など。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - secret 項目はマスク表示、デフォルトや選択肢をサポート。保存前の確認を実施。
  - validate_config.py
    - 起動前チェック用 CLI。必須環境変数・KABUSYS_ENV 値・DB パス・config/*.yaml の存在とパース検証（PyYAML がない場合はパース検証をスキップして警告）。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - 既存ハンドラのクリーンアップ、LOG_LEVEL / LOG_DIR の解決順を提供。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力を継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。アクセス権限や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の重み計算。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用して、上限超過セクターの候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方式に対応した株数計算ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer による保守的見積もり、残差処理による追加配分ロジック等を実装。
- モニタリング / DB 初期化
  - run_* スクリプトから呼び出される init_monitoring_db（monitoring.monitoring_db を想定）を参照して、監視用テーブルが存在することを保証する初期化呼び出しを行う設計。
  - DuckDB 連携: duckdb 接続を受け取る構成（分析用 DB として duckdb を利用）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計し、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を計算してレポート出力する CLI を追加。
    - パス指定オプション (--db, --from, --to) をサポート。各種閾値（稼働率 99%、成功率 90% 等）で PASS/FAIL 判定を行うユーティリティを含む。
- 研究モジュール（未完部分あり）
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials を使ったファクター計算基盤（モメンタム、MA200乖離、ATR、出来高等）を実装する設計。モジュール冒頭に定数と calc_momentum の骨組みを用意（実装続きあり）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- 環境変数の取り扱いについて、.env は Git へ絶対にコミットしない旨をドキュメントに明記（config_setup が生成する .env ヘッダに記載）。

Notes / 運用に関する留意点
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数値が不正・非正数の場合にデフォルト 60 秒へフォールバックして警告を出す。
- run_execution/run_monitoring は data/stop_requested.flag を存在チェックして安全停止する仕組みを採用している。起動時にフラグが立っていると起動しない挙動がある。
- config.validate_config により本番環境（KABUSYS_ENV=live）では特別な警告（LINE 未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）を出す。
- process_priority, logging_setup などは権限や環境によって一部機能がスキップされる可能性がある（失敗時は警告を出力して安全に継続する設計）。

参考
- コード内の docstring / コメントに従い、将来的に:
  - 銘柄別の lot_size を導入する拡張（stocks マスタの導入）や、価格フォールバックの改善等の拡張が想定されています。