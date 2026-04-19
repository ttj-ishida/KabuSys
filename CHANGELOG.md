# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
リリース日はコードベースのスナップショット作成日 (2026-04-19) を使用しています。

## [0.1.0] - 2026-04-19

Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するランチャーを追加。  
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全に分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
    - PID ファイル管理、data/stop_requested.flag による停止フラグ監視、スレッドでエンジンを実行する仕組みを搭載。
    - RiskManager の初期設定値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を組み込み。initial_portfolio_value は broker.get_available_cash() から取得。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）でポーリング間隔を上書き可能。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視 DB の分離方針）および停止フラグ検知でループ終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境読み込み
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み（OS 環境変数が最優先、.env.local が .env を上書き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメントの扱い（クォート有無での挙動差）に対応。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 などのプロパティを提供。PAPER_FILL_MODE（instant|partial|never|reject）などのバリデーションを実装。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジックを含む。

- 設定ユーティリティ CLI
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。  
    - 秘匿項目はマスク表示、既存 .env 読み込み・既存値の再利用、デフォルト値提示、最終的に .env をファイルに書き込み。書式やテンプレートを定義して安全に .env を生成。
  - validate_config.py: 起動前設定検証 CLI を追加。  
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在（および PyYAML があればパース検証）、本番モード時のガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）等を実施。--strict オプションで警告も失敗扱い可能。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - stdout へ StreamHandler、日次ローテートする TimedRotatingFileHandler を root ロガーへ設定。ログディレクトリは引数 / LOG_DIR / デフォルト logs/ の優先順で決定。
    - 既存ハンドラのクリーンアップ、バックアップ保存日数（30 日）などを実装。ファイルハンドラ生成に失敗してもコンソール出力で継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows/Linux/macOS（POSIX）向けの nice/HIGH_PRIORITY クラスを吸収して抽象化。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足などの例外は警告ログを出して安全にスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークでソートして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で配分。すべてのスコアが 0 の場合は等金額にフォールバックして WARNING 出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有を考慮してセクター集中上限（max_sector_pct）を超える場合に新規候補を除外。unknown セクターは上限の対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull:1.0, neutral:0.7, bear:0.3）。未知のレジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づいて各銘柄の発注株数を計算。  
      - risk_based: risk_pct / (price * stop_loss_pct) に基づく算出、max_position_pct による上限、lot_size（デフォルト 100）で丸め。  
      - equal/score: weight による割当てと per-position / aggregate 上限の考慮。  
      - aggregate cap が available_cash を超える場合はスケーリングし、端数（lot 単位）の分配を fractional remainder に基づいて再配分するロジックを実装。cost_buffer により手数料/スリッページを保守的に見積もる。

- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - SQLite（PAPER_TRADING_SQLITE_PATH / 引数 --db）を参照して、system_status / trade_logs / risk_logs などから指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し PASS/FAIL を判定。  
    - しきい値: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。  
    - 日付フィルタ（--from / --to）をサポートし、データ不足時は N/A 表示で安全に処理。

- 研究用モジュール（初期実装）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity の設計方針と定数を定義）。DuckDB 経由で prices_daily / raw_financials を参照してファクターを計算する方針。モジュールは一部実装（モメンタムの定数等）を含むが、ファイル終端がスナップショットで途切れているため今後の追加実装を想定。

Other
- パッケージ初期設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - パッケージエクスポートに portfolio, strategy, execution, monitoring を含める API 層を用意。

Notes / Behavior highlights
- .env の自動ロード順: OS 環境変数 > .env.local > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- run_monitoring は環境によらず production 用の sqlite_path を使用する設計（監視 DB は本番データを想定）。
- run_execution は paper_trading モード時に paper_trading DB を使用することで本番 DB と完全に分離。
- ログは stdout と日次ローテートファイルの両方に出力。ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで継続。
- process_priority / cpu_affinity は権限や OS に依存するため、失敗時は警告を出して安全に処理を続行する。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

---

今後の予定・TODO（コード内コメントより推測）
- price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価）を用いたエクスポージャー計算の改善。
- position_sizing の銘柄別 lot_size 対応（銘柄マスタからの取得）。
- research/factor_research の完全実装（モメンタムなどの計算関数の完了）。
- その他ユーティリティの追加検証（単体テスト、エンドツーエンド検証）。