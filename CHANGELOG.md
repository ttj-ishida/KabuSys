# CHANGELOG

すべての著明な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

- 既存の履歴は semver に従います（MAJOR.MINOR.PATCH）。
- 日付は YYYY-MM-DD 形式です。

## [Unreleased]

## [0.1.0] - 2026-04-19

Added
- 初期リリース: KabuSys パッケージを追加（__version__ = 0.1.0）。
- 設定管理:
  - kabusys.config
    - .env 自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml に基づく）。
    - .env と .env.local の読み込み順序、OS 環境変数保護（上書き禁止）を実装。
    - .env 行パーサー（コメント、export プレフィックス、クォート内エスケープ対応）。
    - Settings クラスを提供（J-Quants / kabu API / DB パス / 各種閾値 / 環境判定などのプロパティ）。
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject のみ許容）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
- 環境設定ウィザード:
  - kabusys.config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。既存値の再利用、シークレット扱い、.env 出力テンプレートを実装。
- 設定検証ツール:
  - kabusys.validate_config: 起動前チェック CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス（親ディレクトリ存在チェック）、config/*.yaml 存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時のガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。--strict オプションで警告も失敗扱いにできる。
- 起動スクリプト:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - 環境が paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用したブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine をデーモンスレッドで起動・停止フラグ検知（data/stop_requested.flag）を実装。
    - 実行中は停止フラグにより安全に engine.stop() を呼び停止できる。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視データベースは環境にかかわらず本番 sqlite_path を参照して初期化（監視テーブルの冪等初期化を実行）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt も正常に扱う。
- ロギング / プロセス制御ユーティリティ:
  - kabusys.utils.logging_setup
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保管）を設定するユーティリティを提供。
    - LOG_DIR/LOG_LEVEL/引数による解決、ログディレクトリ作成失敗時にはファイルハンドラをスキップしてコンソール出力のみでフォールバック。
    - stdout を使用することで cron 等からのリダイレクト運用に配慮。
  - kabusys.utils.process_priority
    - set_process_priority(level) で Windows / POSIX の差を吸収して優先度を設定。失敗時は警告出力してスキップ。
    - set_cpu_affinity(cpu_count) による CPU ピンニング機能を提供（未指定時は何もしない）。アクセス権限や非対応 OS では警告を出力。
- ポートフォリオ構築モジュール:
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計 0 の場合は等分へフォールバックと警告）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、1 セクターの上限超過時は同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投資乗数を返す（bull/neutral/bear -> 1.0/0.7/0.3）。未知レジームは警告して 1.0 にフォールバック。
    - 注記: 価格欠損時のフォールバックは TODO コメントあり（将来的な改善点）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく株数決定。リスクベースの基本式、1 銘柄上限、単元株（lot_size）丸め、aggregate cap（利用可能現金を超える場合の縮小ロジック）を実装。cost_buffer を使った保守的見積り、残差分の lot 単位再配分アルゴリズムを実装。
    - TODO: 将来的に銘柄別 lot_size を導入するための拡張メモあり。
  - パッケージエクスポート（kabusys.portfolio.__init__）を用意。
- 解析 / リサーチ:
  - kabusys.research.factor_research
    - ファクター計算モジュールの骨子を追加（モメンタム / MA200 / ATR / 出来高等を想定）。DuckDB 接続を受け prices_daily / raw_financials を参照する設計（関数の実装は一部）。
- ツール:
  - kabusys.tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を参照（または --db オプション）。
    - システム稼働率（system_status）、注文成功率 / 送信率（trade_logs）、リスク却下数（risk_logs）、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定（閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - P95 計算、日付フィルタ（ISO8601 UTC 文字列）に対応。
- その他:
  - monitoring DB 初期化関数 init_monitoring_db を呼ぶ箇所を run_execution / run_monitoring に追加して監視テーブルの存在を保証（冪等）。
  - 実行時に PID ファイルを受け渡す仕組みを用意（ExecutionEngine / SystemMonitor の pid_file パラメータ）。

Changed
- 起動スクリプトでの共通方針:
  - 起動時にプロセス優先度を「最初に」 high に設定するよう統一（実行および監視スクリプト）。
  - ログ出力は stdout をデフォルトにし、ファイル出力はログディレクトリ作成成功時のみ有効化。

Fixed
- MONITOR_POLL_INTERVAL の不正値（負数・0・非整数）に対して警告してデフォルトにフォールバックするように改善（time.sleep での ValueError 回避）。
- .env パーサーにおいてクォート内のバックスラッシュエスケープを考慮して正しく値を復元するように実装。

Notes / TODO
- apply_sector_cap: price_map に値がない（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメント。前日終値や取得原価によるフォールバックの検討が記載されている。
- position_sizing: 将来的に銘柄別の lot_size を導入するための拡張メモあり。
- research.factor_research の一部関数は実装が途中（ファイル末尾が切れている）であり、追加実装が必要。

Breaking Changes
- なし（初期リリースにつき過去互換性の懸念はありません）。

---

（注）この CHANGELOG はコードベースのソースコードから推測して作成しています。実際のリリースノートとして使用する場合は必要に応じて補足・修正してください。