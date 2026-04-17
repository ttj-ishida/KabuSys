# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
日付は本リリース作成日です。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装: KabuSys 自動売買システムのコアモジュールを追加。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 環境・設定管理
  - .env の自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い等に対応。
  - 環境変数読み取りラッパー `Settings` を実装。主なプロパティ:
    - J-Quants / kabu API トークン・パスワード、LINE 通知設定、DB パス、監視／閾値設定、実行環境フラグ（development / paper_trading / live）など。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。

- 環境設定ツール（CLI）
  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - デフォルト値、選択肢、シークレット項目のマスク表示、保存確認を備える。
  - `kabusys.validate_config`:
    - 起動前チェック CLI を追加。必須環境変数の有無、KABUSYS_ENV の妥当性、DB パスの存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、ライブ環境向けガード等を実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行エントリポイント
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と分離して専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計をサポート。
    - 停止管理: data/stop_requested.flag を検知して安全に停止する仕組み、起動時のプロセス優先度設定（High）が組み込み。
    - 実行エンジンはスレッドで動作し、停止フラグ検出時に Engine.stop() を呼び出して終了する。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告後デフォルトにフォールバック。
    - 監視用 DB は環境に関係なく production の sqlite_path を使う旨の挙動（設計上の注意）。
    - 停止フラグ検出、check_once() の例外キャッチとロギング、リソースクリーンアップ（DB接続クローズ）を実装。

- モニタリング DB 初期化フロー
  - `monitoring_db.init_monitoring_db` の呼び出しにより監視用テーブルが存在することを保証（冪等）。

- Execution 系のコンポーネント群（起動時に組み合わせて使用）
  - BrokerClientFactory（ブローカークライアント生成、paper/live を透過）。
  - OrderRepository、OrderManager、RiskManager（RiskConfig を利用して複数パラメータで初期化）、Reconciler、ExecutionEngine（pid ファイル管理、duckdb 連携）を組み合わせる起動フローを実装。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用の SQLite DB から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）等を集計しレポート出力する CLI を追加。
    - デフォルト閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）による PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）に対応。

- ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）
  - `portfolio.portfolio_builder`:
    - 候補選定（score 降順、tie-break に signal_rank）select_candidates。
    - 等分配 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等分配にフォールバック、警告を出力）。
  - `portfolio.risk_adjustment`:
    - セクター集中制限 apply_sector_cap（既存保有のセクター割合が上限超過の場合に新規候補を除外、"unknown" セクターは除外対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear を扱い、未知の値はフォールバックで 1.0 として警告）。
  - `portfolio.position_sizing`:
    - position sizing アルゴリズム実装（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベース sizing（risk_pct, stop_loss_pct を使用）と等分配・スコア配分をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、全体投下上限（max_utilization）、コストバッファ(cost_buffer) を考慮した aggregate cap スケーリング（スケールダウン → 残余を fractional remainder に基づき lot 単位で配分）を実装。
    - 価格欠損時のスキップやログ出力等の安全策を実装。

- 研究用ファクター計算
  - `research.factor_research`:
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照するファクター計算機能（momentum, volatility, liquidity 等）の実装を開始。
    - モメンタム（1M/3M/6M、MA200乖離）、ATR ベースのボラティリティ、20日平均売買代金等を計算するクエリを含む。

- ユーティリティ
  - `utils.process_priority`:
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を抽象化して set_process_priority("high"|"normal"|"low") を提供。権限不足等の例外は警告で安全に無視。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能（未サポート環境は警告）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 備考
- run_monitoring はドキュメンテーション上「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明記されており、環境により監視 DB を切り替える場合は設計を見直す必要があります。
- .env の取り扱いは安全上の注意（.env を絶対にリポジトリにコミットしない等）を README 等で明示することを推奨します。
- 一部の機能（DuckDB を用いるファクター計算や ExecutionEngine の細部）は外部依存（duckdb, psutil, PyYAML 等）を前提とします。必要パッケージはパッケージング時に requirements に明記してください。

---

今後のリリースで想定される改善点（ロードマップ候補）:
- 銘柄ごとの lot_size を支援するためのマスタ情報反映。
- position_sizing のテストカバレッジ強化と境界ケースの堅牢化（価格欠損時のフォールバック価格）。
- monitoring/monitoring_db の詳細設計とメトリクスの拡張（ディスク/メモリ/CPU 閾値のしきい値動的変更等）。