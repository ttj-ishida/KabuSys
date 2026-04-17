# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
この CHANGELOG はソースコードから推測できる変更・機能を元に作成しています（実装コメントや TODO を含む）。

## [Unreleased]

### Added
- news_nlp モジュールの骨格と設計方針を追加（OpenAI を使ったニュースセンチメント集計の実装予定）。
  - ニュース時間ウィンドウ計算、バッチ処理・リトライ方針、出力 JSON フォーマット仕様などを定義。
  - API キー解決ロジック、トークン肥大化対策（記事数・文字数上限）、スコアのクリップなどの定数を追加。
- ai/news_nlp の処理フローや安全策（部分失敗時の既存スコア保護）を設計メモとして整備。

### Changed
- news_nlp はまだ途中実装（ソース末尾が途中で切れているため追加実装が必要）。

### Known issues / TODO
- apply_sector_cap: price が欠損（0.0）時にエクスポージャーが過少見積りになる問題を将来的に前日終値や取得原価で補う予定（ソース中に TODO コメントあり）。
- position_sizing: 銘柄別の単元（lot_size）を将来的に stocks マスタから取得する設計へ拡張予定（現在は全銘柄共通の lot_size）。
- ai/news_nlp の最後の処理（記事取得・API 呼び出し・結果書き込み）は未完。リリース前に実装・テストが必要。

---

## [0.1.0] - 2026-04-17

初回公開リリース（ソースコードの現状を反映）。

### Added
- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを構成。
    - エンジンはスレッドで実行、外部停止フラグ（data/stop_requested.flag）で安全に停止可能。実行 PID を data/execution.pid に記録する想定。
    - RiskManager 初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトで適用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト: 60 秒）。
    - 監視処理は監視用テーブルの初期化（init_monitoring_db）と DuckDB 接続を行う。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
    - export KEY=val 形式やクォート・エスケープ、インラインコメントなどに対応した .env パーサを実装。
    - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。
    - Settings クラスを導入し、環境変数の型変換 / バリデーションを提供（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE のバリデーション）。
    - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や監視関連設定（PID/KILL フラグパス、しきい値）を管理。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選別。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全銘柄スコアが 0 の場合はフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター比率に基づき新規候補を除外）。"unknown" セクターは除外対象外として扱う。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング、未知レジームは警告と 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based","equal","score") に応じて発注株数を計算。
      - リスクベースの計算（risk_pct, stop_loss_pct）と単元丸め（lot_size）。
      - per-position および aggregate cap（available_cash）によるスケールダウン処理。
      - cost_buffer を使った手数料・スリッページ見積りを考慮。
      - 合成スケーリング後の残差配分（lot 単位）を実装。

- 監視 / ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティ（set_process_priority）を追加。Windows/POSIX の差分を吸収。
    - CPU affinity 設定関数（set_cpu_affinity）を追加。
    - 権限不足や未対応 OS の場合のフェールセーフを実装。
  - run_* スクリプトで起動時にプロセス優先度を "high" に設定するよう適用。

- 研究 / リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: EPS/ROE に基づく PER/ROE 計算（raw_financials の最新レコードを使用）。
    - 各関数は欠損データ処理・ウィンドウ件数チェックを実装。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（引数でホライズン指定可能、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・最小レコード数チェック）。
    - rank / factor_summary: ランク変換、統計サマリー（count/mean/std/min/max/median）を純粋 Python で実装。
  - research/__init__.py に主要関数をエクスポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力。
    - フィルタ期間指定（--from / --to）・DB パス指定（--db）に対応。
    - P95 計算、SQLite が存在しない場合のエラーメッセージ出力、OperationalError を考慮したフォールバック処理を実装。
    - 判定基準（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）をデフォルトで適用。

- パッケージ初期化
  - package version: kabusys.__init__.__version__ = "0.1.0"
  - kabusys/portfolio, kabusys/research, kabusys/tools 等のエクスポート整備。

### Fixed
- .env パーサの堅牢性向上
  - export キーワード対応、クォート中のバックスラッシュエスケープ処理、コメント扱いの改善。
  - override / protected オプションによる環境変数上書き制御を実装。

### Changed
- 監視実行時の DB 運用方針
  - run_monitoring は KABUSYS_ENV にかかわらず「本番」の sqlite_path を使用して monitoring テーブルに接続する旨が明記（監視は環境に依存しない運用方針）。

### Documentation
- 各モジュールに docstring と設計方針・注意事項を詳細に追記（PortfolioConstruction.md / StrategyModel.md 等を参照する旨のコメントあり）。

### Security
- OpenAI API キーの扱い: 関数引数での注入を受け付け、未設定時は明示的にエラーとする（環境変数依存の明示化）。

---

## 参考（実装上の注意点）
- データベース接続は sqlite3 / duckdb を利用。監視テーブルの初期化関数 init_monitoring_db を起動時に呼び出しているため、テーブル存在性は保証される想定。
- run_execution の RiskManager 初期化で broker.get_available_cash() を利用して initial_portfolio_value を設定しているため、BrokerClient の get_available_cash 実装が必要。
- CPU affinity / priority の設定は権限によって失敗する可能性があるため、ログで警告を出して安全にスキップする実装になっている。
- research / factor_research は DuckDB 上の prices_daily / raw_financials テーブルスキーマに依存。データ不足時の None ハンドリングが施されている。

---

もしリリースノートを別バージョンごとに分割したい、あるいは各項目に関連する PR / issue 番号や作者情報を付加したい場合は、対象の範囲（モジュール単位／コミット範囲）を指定してください。