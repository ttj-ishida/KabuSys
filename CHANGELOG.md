CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 実行・監視のエントリポイントを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite（data/paper_trading.db をデフォルト）を使用する。起動時にプロセス優先度を "high" にセットし、停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の sqlite_path を使用するよう実装。

- 環境・設定関連のユーティリティを追加
  - config.py: .env 自動読み込み（.env / .env.local、OS 環境変数保護）、.env パースロジック（export 対応、クォート/エスケープ、インラインコメント処理）、Settings クラス（各種環境変数の取得・バリデーション）を実装。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。デフォルト値・選択肢・シークレット入力対応、保存確認を実装。
  - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL バリデーション、DB パスの親ディレクトリチェック、YAML パース検証（PyYAML が存在する場合）、本番時の追加ガードを実装。--strict オプションで警告を失敗扱いに変更可能。

- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。コンソール (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。LOG_DIR/LOG_LEVEL の解決順、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows と POSIX 系の差分を吸収）および CPU affinity 設定を実装。権限不足や未対応 OS の場合は安全にスキップする。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）
  - portfolio/portfolio_builder.py: 候補選出 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバック挙動を採用）。
  - portfolio/position_sizing.py: allocation_method("risk_based", "equal", "score") に基づく株数決定ロジックを実装。単元株（lot_size）丸め、1銘柄上限・全体利用率上限、コストバッファを用いた aggregate cap スケーリング、端数の再配分ロジック等を含む。

- 解析・レポートツールを追加
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs テーブルを参照して稼働率・注文成功率・送信率・レイテンシ（P95 など）を算出し、閾値（稼働率 99%、成立率 90% など）に基づき PASS/FAIL を判定。--from/--to/--db オプションをサポート。

- リサーチ用ファクター計算フレームワークを導入
  - research/factor_research.py: モメンタムや MA200 乖離、ATR 等を計算するための骨組みを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。（注: 一部実装が継続中）

Changed
- パッケージ初期化
  - __init__.py にバージョン (0.1.0) と公開モジュール一覧を追加。

Fixed
- .env パーサーの堅牢性向上
  - _parse_env_line: export で始まる行の対応、クォート内のバックスラッシュエスケープ処理、クォートなしのインラインコメント判定の改善を行い、より現実的な .env 書式に対応。

- ロギング周りの堅牢化
  - setup_logging: ログディレクトリ作成エラー時にファイル出力を安全にスキップし、コンソール出力のみで継続するように改善。また既存ハンドラを適切に flush/close してから差し替えるようにした。

- プロセス優先度設定の耐障害性強化
  - set_process_priority / set_cpu_affinity: 権限不足や未実装メソッド発生時に警告を出してスキップするよう改善。

Performance
- ポートフォリオ関連関数は全て純粋関数（副作用なし、DBアクセスなし）として実装されているため、ユニットテストや高速なメモリ内演算に最適化。

Documentation
- 各モジュールに docstring を追加し、設計方針（参照テーブル、期待される入力/出力、フォールバック挙動等）を明記。

Breaking Changes
- 監視スクリプト (run_monitoring.py) は「環境にかかわらず」Settings.sqlite_path（本番用 sqlite_path）を使用する挙動になっています。環境ごとに監視用 DB を分離したい場合は Settings の環境変数を調整するか、コード側の変更が必要です。

Notes / Known issues
- research/factor_research.py は実装途中で末尾が切れている箇所があります。完全なファクター計算ロジックは今後のリリースで補完予定です。
- position_sizing.calc_position_sizes における価格欠損（price == 0）の扱いに関して TODO コメントあり。将来的に前日終値等のフォールバックを検討。

安全上の注意
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。

--- 
作成: 自動推測による CHANGELOG（コードベースの内容から生成）