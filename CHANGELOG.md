# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベースから推測した機能追加・仕様をまとめたものであり、実装の意図や既定値はソースコードを参照しています。

-----------------------------------------------------------------------
[0.1.0] - 2026-04-18
-----------------------------------------------------------------------

Added
- 初期リリース。KabuSys のコアユーティリティ・実行コンポーネントを追加。
  - パッケージメタ情報
    - バージョン: `0.1.0`（src/kabusys/__init__.py）
  - 起動スクリプト
    - run_monitoring: SystemMonitor のポーリングループ起動。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の `sqlite_path` を使用。停止はプロジェクト直下の `data/stop_requested.flag` による（src/kabusys/run_monitoring.py）。
    - run_execution: ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離。プロセス PID ファイルと停止フラグを扱う（src/kabusys/run_execution.py）。
  - 設定管理
    - Settings クラスで各種環境変数を統一的に扱う（env 判定、DB パス、LINE トークン、閾値、paper_fill_mode の検証など）。デフォルト値やバリデーションを実装（src/kabusys/config.py）。
    - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を OS 環境を保護しつつ読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
    - .env のパースはシングル/ダブルクォート、`export KEY=...` 形式、インラインコメント等に対応。
  - 設定支援・検証 CLI
    - config_setup: 対話式ウィザードで .env を初期作成・更新。主要項目（KABUSYS_ENV、API トークン、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に編集・保存（src/kabusys/config_setup.py）。
    - validate_config: 起動前チェック CLI。必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml（PyYAML があればパース検証）・本番向けガードを検証。`--strict` で警告も失敗扱いにできる（src/kabusys/validate_config.py）。
  - ログ・プロセス管理ユーティリティ
    - logging_setup: ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を追加。ログレベル解決順や出力ディレクトリ解決を実装。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続（src/kabusys/utils/logging_setup.py）。
    - process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を最初 N コアに固定するユーティリティも提供（src/kabusys/utils/process_priority.py）。
  - Execution 関連コンポーネント（参照のみ、実実装は別モジュールへ）
    - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てと起動フロー定義（src/kabusys/run_execution.py）。
    - RiskManager に初期パラメータ（max_position_pct=0.20, max_utilization=0.80 など）を設定し、`initial_portfolio_value` をブローカーの利用可能現金から取得する設計。
  - 監視関連データベース
    - monitoring 用 DB 初期化ユーティリティ呼び出しを各起動スクリプトで実行（冪等）。DuckDB との併用（analytics 用）もサポート。
  - ポートフォリオ構築ロジック（純関数群）
    - portfolio_builder:
      - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等配分とスコア加重（全スコアが 0 の場合は等配分へフォールバック、警告ログあり）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限（デフォルト 30%）を既存ポジションに対して評価し、上限を超過しているセクターの新規候補を除外。unknown セクターは上限適用除外。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）を返す。未知のレジームは 1.0 へフォールバックして警告ログ（src/kabusys/portfolio/risk_adjustment.py）。
    - position_sizing:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。単元株（lot_size）で丸め、per-stock 上限や aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的計算、残余キャッシュを用いた再配分ロジックを実装（src/kabusys/portfolio/position_sizing.py）。
  - 解析・調査ツール
    - tools/paper_verification_report: Paper Trading 用 SQLite DB（`PAPER_TRADING_SQLITE_PATH`）から稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）・リスク却下数を集計し、基準値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）に基づいて PASS/FAIL 判定するレポート生成 CLI を実装。日付フィルタ（--from/--to）と DB パスオーバーライド (--db) に対応（src/kabusys/tools/paper_verification_report.py）。
  - リサーチ / ファクター計算（骨格）
    - research/factor_research: DuckDB の prices_daily / raw_financials を使ったモメンタム / バリュー / ボラティリティ / 流動性ファクター計算モジュールの設計と一部実装（ファイル末尾は未完の可能性あり）（src/kabusys/research/factor_research.py）。

Changed
- （初版のため過去からの変更なし）

Fixed
- （初版のため過去からの修正なし）

Deprecated
- なし

Removed
- なし

Security
- 機密情報（API トークンやパスワード）は .env に保存する設計。config_setup は .env を生成する際に「.env を絶対に Git にコミットしないこと」を明示。

Notes / 実装上の注意点（コードから推測）
- run_monitoring は監視 DB に対して環境にかかわらず production の sqlite_path を使用する設計（意図的に本番監視 DB を参照）。運用時は注意が必要。
- run_execution は paper_trading の場合に専用 DB に切り替えるが、monitoring テーブルは冪等に初期化されるため双方の干渉に注意。
- .env パーサはクォートやエスケープを細かく扱うが、完全なシェルの挙動と同一ではない点に留意。
- position_sizing の価格欠損（price が 0.0）に対する TODO コメントあり。将来的に前日終値などのフォールバックが必要。
- process_priority / set_cpu_affinity は権限不足や未サポート環境で安全にスキップする設計（警告ログ）。

-----------------------------------------------------------------------

未記載のバグ修正や細かい実装差分がある可能性があります。詳細は該当ソースファイルの docstring / コメントを参照してください。