CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に準拠して記述しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に準拠します。

v0.1.0 — 2026-04-22
-------------------

初期リリース。自動売買システム KabuSys の基礎機能群を実装しました。主な追加点は以下のとおりです。

Added
- 設定・環境変数関連
  - Settings クラスを追加し、環境変数経由でアプリ設定を取得する仕組みを実装（src/kabusys/config.py）。
    - サポート項目: J-Quants / kabu API トークン、DB パス（DUCKDB_PATH / SQLITE_PATH）、ログレベル、KABUSYS_ENV（development / paper_trading / live）など。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID / KILL フラグ、監視閾値などのプロパティを提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロード無効化をサポート。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env → .env.local の順、OS 環境変数を保護）。
  - 設定ウィザード CLI を実装（src/kabusys/config_setup.py）。対話式で .env を生成・更新可能。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。必須環境変数や config/*.yaml の存在・パース確認、--strict モードで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/live に応じたクライアント選択想定）。
    - ExecutionEngine を別スレッドで実行し、 data/stop_requested.flag による停止モードをサポート。実行用 PID ファイルの取り扱いあり。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する旨の仕様を明示（docstring）。
    - SystemMonitor.check_once() を周期的に呼び、停止フラグ（data/stop_requested.flag）や KeyboardInterrupt を扱う。

- ロギング / プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイルを出力。デフォルトログディレクトリは logs/。
    - ログファイルローテーションは日次、30 日分保持。
    - LOG_LEVEL / LOG_DIR の優先順位に従い解決。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS 等）を吸収して set_process_priority(level: "high"|"normal"|"low") を提供。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定可能。アクセス権限や未サポート OS は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・上位 N を選択
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重（スコア合計 0 の場合は等分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: market_regime に基づく乗数 (bull=1.0, neutral=0.7, bear=0.3) を返す。未知レジームは 1.0 にフォールバック。
  - 発注株数算出・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数決定、単元(lot_size)丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer の考慮、残差処理によるロット追加配分などを実装。
    - リスクベース方式は stop_loss_pct, risk_pct を用いてポジションサイズを算出。

- Paper Trading 向けツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し、PASS/FAIL 判定（デフォルト閾値を定義）を出力。
    - コマンドライン引数 --from / --to / --db をサポート。環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可。

- リサーチ基盤（着手）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity に関する設計方針と定数定義を含む。calc_momentum の実装開始（ファイル末尾で途中）。

- パッケージ初期化
  - パッケージの __version__ を 0.1.0 に設定（src/kabusys/__init__.py）。
  - portfolio パッケージのエクスポートを整理（src/kabusys/portfolio/__init__.py）。

Changed
- なし（初期リリースのため変更履歴はありません）。

Fixed
- なし（初期リリースのため修正履歴はありません）。

Notes / Implementation details
- DB 接続
  - 実行/監視ともに SQLite（monitoring 用と paper_trading 用に分離）及び DuckDB（分析用）への接続処理を実装。monitoring 用は init_monitoring_db によるテーブル準備を行う（呼び出し有）。
- 停止制御
  - data/stop_requested.flag による外部停止制御を採用。run_execution/run_monitoring は起動時 / ループ中にこのフラグを確認して安全に停止する設計。
- エラーハンドリング
  - 監視ループ内で monitor.check_once() の例外を捕捉してログ出力し、次ポーリングに移る耐障害性を実装。
- セキュリティ・運用
  - .env ファイルは Git にコミットしない旨をウィザードの出力で明示（config_setup）。

Known limitations / TODO
- ファクター計算モジュール（research/factor_research.py）は途中の実装で、完全な計算ロジックは未完（calc_momentum が途中で終端）。
- position_sizing の price 欠損（0.0）に対するフォールバック価格（前日終値等）の処理は TODO コメントで指摘あり。
- BrokerClientFactory / ExecutionEngine 等エンジン内部の詳細実装（発注ロジック・ブローカ抽象）は本リリースの外部コンポーネントとして扱われているため、統合テストが必要。

Security
- 本リリースでは機密値（API トークン・パスワード）を .env に格納する設計となっているため、.env をリポジトリに含めないようドキュメント（config_setup にも注記）で注意を促しています。

----------------------------------------
今後のリリースでの改善予定例（案）
- research/factor_research の完実装とテスト
- ExecutionEngine の統合テスト、ブローカーモック群の整備
- YAML ベースの config ファイルの型チェック強化
- ログおよびメトリクスの外部可視化（Prometheus / Grafana 等）対応

以上。必要であれば各変更点に対する詳細な開発ノートや対応したソース行の抜粋を作成します。