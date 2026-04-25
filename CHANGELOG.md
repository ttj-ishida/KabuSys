CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-25
------------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
- コア設定/環境管理
  - 環境変数読み込み機能を実装（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、各種設定値（J-Quants、kabu API、DB パス、Paper Trading 設定、監視しきい値、環境種別など）をプロパティ経由で取得。値検証を実施（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）。
- 設定支援 CLI
  - 環境設定ウィザード（kabusys.config_setup）を追加。対話式で .env を作成/更新し、機密項目はマスク表示して保存。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば内容検証）などをチェック。--strict モードで警告も failure 扱いにできる。
- 起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - Paper Trading 環境では settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。KABUSYS_ENV=paper_trading の場合は MockBroker を利用する設計（BrokerFactory 経由）。
    - Broker / OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。エンジンは別スレッドで run_session を実行し、 data/stop_requested.flag により安全に停止可能。
    - 起動時・終了時に SQLite / DuckDB 接続を管理。
  - 監視（monitoring）起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - SystemMonitor.check_once() をポーリングで実行し、例外はログに記録して次ポーリングへ継続。
- ロギング・プロセス管理ユーティリティ
  - 統一的なログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）で logs/<app_name>.log に出力。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX (Linux/Mac/FreeBSD) の差分を吸収して優先度を設定。アクセス権限や未対応 OS にはフォールバックして警告を出す。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
- データベース・モニタリング
  - monitoring 用 DB 初期化ユーティリティ呼び出し（init_monitoring_db）を起動スクリプトに統合（起動時に監視テーブル存在を保証、冪等）。
  - DuckDB 接続を利用する設計（analysis 向けの連携を想定）。
- Paper Trading サポート & レポートツール
  - Paper Trading 用の検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を参照し、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - 各種閾値による PASS/FAIL 判定ロジックを実装（稼働率 99%、注文成功率 90% 等）。
    - P95 計算、日付フィルタ指定、DB ファイル存在チェック、SQL 実行時の例外処理を備える。
- ポートフォリオ構築モジュール（純関数群）
  - portfolio パッケージを追加（kabusys.portfolio）。
  - 候補選定と重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順、同点時は signal_rank の小さい方を優先して上位 N 件を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックして警告）。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 にフォールバック。
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じて発注株数を算出。lot_size（単元）で丸め、max_position_pct / max_utilization による上限、cost_buffer を考慮した aggregate cap（スケールダウン）処理を実装。残余キャッシュで端数を lot 単位で追加配分するロジックを含む。
  - portfolio パッケージ __all__ を整備して主要関数をエクスポート。
- リサーチ（雛形）
  - research.factor_research モジュールを追加（ファクター計算の設計・定数、calc_momentum の実装開始）。DuckDB から prices_daily / raw_financials を参照してモメンタム等を算出する方針を明記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 機密情報（API トークン等）は .env に保持する運用を想定し、config_setup で .env を生成する際に Git コミット禁止の注記を追加。

Known issues / Notes
- research.factor_research の calc_momentum 実装は途中（ファイル末尾が未完）であり、ファクター計算群は今後の実装・整備が必要。
- 一部のファイルで外部依存（psutil, duckdb, PyYAML 等）に対する ImportError や権限エラーに対してフォールバック処理を実装しているが、本番環境での動作確認を推奨。
- PAPER_FILL_MODE 等の環境変数値の不正入力時は ValueError を送出するため、validate_config による事前チェックを強く推奨。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみで継続する仕様（エラー時にデバッグログがファイルに残らない可能性あり）。

How to use (短いメモ)
- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。