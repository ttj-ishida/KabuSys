# Changelog

すべての注目すべき変更を記録します。  
注: 以下はリポジトリ内のソースコードを参照して推測・要約して作成した変更履歴です（コミット履歴そのものではありません）。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース相当の主要コンポーネントを追加。
- 設定管理
  - Settings クラスを導入し、環境変数を型付きプロパティで取得可能に。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサを実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理のルール）。
  - 必須環境変数取得用の _require ユーティリティを追加。
  - 各種設定プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEM/DISK 閾値 等）を追加。
  - PAPER_FILL_MODE の入力検証（有効値: instant|partial|never|reject）を実装。

- CLI ツール
  - config_setup: 対話式 .env ウィザード（生成・更新）を追加。既存値マスク表示や秘密項目扱いに対応。書き出しテンプレートに注意書き（.env をコミットしない）を含む。
  - validate_config: 起動前設定検証コマンドを追加。必須環境変数やパス、config/*.yaml の存在・パース確認、KABUSYS_ENV の整合性チェックなどを実行。--strict オプションで警告を失敗扱いにできる。
  - tools/paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。期間指定（--from / --to / --db）に対応し、稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL 判定を出力する。デフォルト DB は data/paper_trading.db。

- 実行・監視エントリポイント
  - run_execution: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を設定。paper_trading 環境時は paper 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する設計。
    - BrokerClientFactory を通じたブローカークライアント生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値は broker.get_available_cash() から取得。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して monitoring DB を初期化（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。Ctrl+C（KeyboardInterrupt）に対応してクリーンに終了。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装。スコア合計ゼロ時のフォールバック警告を含む。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。
  - portfolio.position_sizing: calc_position_sizes（リスクベース / equal / score ベースの株数決定、単元株単位で丸め、aggregate cap によるスケールダウンロジック、cost_buffer の考慮）を実装。
  - portfolio パッケージで上記関数をエクスポート。

- リサーチ
  - research.factor_research: DuckDB を使ったファクター計算モジュールを追加。calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比率）を実装。prices_daily テーブル参照、データ不足時の None 扱い等を考慮。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加。Windows と POSIX 系（Linux/Mac/FreeBSD）の差異を吸収し、権限不足や未対応環境では警告を出して安全にスキップする。

- DB/分析基盤
  - DuckDB 接続を分析用途（research, engine 等）で利用する設計を導入。デフォルトパスは data/kabusys.duckdb。
  - SQLite は監視・注文履歴用（data/monitoring.db）と paper_trading 用（data/paper_trading.db）に分離可能。

- ペーパートレード検証閾値（tools/paper_verification_report）
  - 稼働率: 99.0%
  - 注文成功率(Fill): 90.0%
  - 送信率(Send): 95.0%
  - P95 レイテンシ: 200 ms

### Changed
- .env ロードの優先順位と挙動を明確化
  - 読み込み順: OS環境 > .env.local > .env。既存 OS 環境変数は protected として上書きを抑制。
  - _load_env_file に override / protected 引数を追加し、上書きルールを制御。
- run_execution / run_monitoring の起動シーケンス調整
  - 起動直後にプロセス優先度を設定するようにし、リソース割り当ての優先制御を強化。
  - DB 初期化（init_monitoring_db）は冪等に呼び出され、必要な監視テーブルが存在することを保証するようにした。
- モニタリング用のポーリング間隔設定方法を追加（MONITOR_POLL_INTERVAL 環境変数）。
- run_execution: paper_trading 環境時に専用 SQLite を使用するようにして、本番データと完全分離する仕様に変更。

### Fixed / Defensive improvements
- .env パーサの堅牢性強化
  - export プレフィックス、クォート内のエスケープ、コメント扱いの改善により .env の柔軟な記述に対応。
- process_priority / set_cpu_affinity
  - 権限不足や非対応 OS での例外をキャッチして警告に置き換え、起動失敗を防止。
- 各種クエリ/集計でデータ欠損に対して None を利用するなど安全にフォールバックする実装を追加（例: ファクター計算、検証レポート集計、レイテンシ P95 計算）。
- run_execution/run_monitoring での停止フラグ検出ロジックを統一（data/stop_requested.flag を検知して安全に終了）。

### Internal / Documentation
- パッケージ __init__.py にバージョン情報 __version__ = "0.1.0" を追加。
- 各モジュールに docstring と使用例・設計メモを追加して可読性を向上。
- config_setup の出力テンプレートに .env を Git にコミットしない旨の注記を含める。

---

今後の作業（提案）
- 単体テストと CI の追加（特に .env パーサ、position sizing の数値ロジック、factor_research の SQL 部分）。
- 銘柄ごとの lot_size をサポートするための拡張（position_sizing の TODO に記載）。
- 監視・リスク閾値の運用チューニングとアラート出力（LINE 連携の検証）。