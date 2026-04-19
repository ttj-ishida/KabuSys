Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 廃止 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
---------

（現在未リリースの変更はここに記載します）

0.1.0 - 2026-04-19
-----------------

Added
- パッケージ初期リリースを追加。
- 実行エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、ブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、スレッドでのエンジン実行と停止フラグ監視を実装。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。停止フラグファイルで終了。
- 設定/環境管理:
  - config.py: 環境変数・設定管理モジュールを追加。.env/.env.local の自動ロード機能（プロジェクトルート検出）と、クォートや export 構文、インラインコメントの取り扱いに対応したパーサを実装。必須環境変数取得ヘルパや env 判定（development/paper_trading/live）を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。既存 .env の読み込み・マスク表示・確認保存機能を提供。
  - validate_config.py: 起動前に .env および config/*.yaml の妥当性を検証する CLI を追加。--strict モードで警告も失敗扱いにできる。
- ユーティリティ:
  - utils/logging_setup.py: 統一されたロギング設定ユーティリティを追加。コンソール (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。ログディレクトリ作成失敗時はフォールバックしてコンソール出力のみで動作。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。Windows / POSIX(nice) に対応し、未対応 OS や権限不足時は警告を出して安全にスキップする。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合に等分配へフォールバックする挙動を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジームはフォールバック（1.0）し警告を出す。
  - portfolio/position_sizing.py: 株数計算ロジックを実装。allocation_method に応じて risk_based / equal / score をサポート。lot 単位丸め、ポジション上限、aggregate cap（利用可能現金でリスケール）、cost_buffer（手数料/スリッページ見積り）対応を含む。
  - portfolio/__init__.py: 上記関数を公開 API としてエクスポート。
- リサーチ:
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム等の計算方針と定数を含む）。（注: ファイル末尾に続きあり）
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率（Fill/Send）、リスク却下数、レイテンシ（平均/最大/P95）を計算して PASS/FAIL 判定を出力。P95 計算や期間フィルタ (--from/--to)、DB パス指定 (--db / 環境変数) に対応。
- パッケージ情報:
  - __init__.py: パッケージのバージョン (0.1.0) と主要サブパッケージを定義。

Changed
- 環境変数自動ロード:
  - .env 自動ロードはプロジェクトルート検出に基づくようにし、プロジェクトルートが見つからない場合は自動ロードをスキップするよう変更。テストや特殊環境用に KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - .env.local を上書き読み込みできるようにし、OS 環境変数は保護（protected）して上書きされないように実装。
- ロギング:
  - ログ出力は標準的に stdout を使う（cron などでのリダイレクトを想定）。ログレベルとログディレクトリは引数・環境変数・デフォルトの順で解決するよう明確化。
- run_monitoring:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明確化（監視 DB は別管理せず常に監視対象 DB を使う設計）。
- run_execution:
  - paper_trading 環境時に paper_sqlite_path を使って DB を分離する仕様を採用（本番 DB との完全分離を実現）。

Fixed
- 環境変数パーサの強化:
  - export KEY=val 形式、シングル/ダブルクォート値、バックスラッシュエスケープ、インラインコメントの扱いなどを堅牢に処理するよう改良。
- MONITOR_POLL_INTERVAL の取り扱い:
  - 無効値（非数、0 以下など）が指定された場合にデフォルト値へフォールバックし、ログで警告を出すようにした（time.sleep に渡す不正値による ValueError を回避）。
- ログハンドラ重複防止:
  - setup_logging は既存ハンドラを一度クリアしてから再設定するようにして、二重出力を防止。
- process_priority:
  - 権限不足や非対応 OS で発生する例外を捕捉して警告ログを出すようにし、起動失敗を防止。
- DB 初期化:
  - init_monitoring_db を idempotent に呼び出し、monitoring 用テーブルが存在することを保証（複数回呼び出しても安全）。

Deprecated
- なし

Removed
- なし

Security
- なし

補足 / 注意事項
- Paper Trading と Live（本番）はデータストアを分離することを推奨しています（実装でも paper_trading 用 SQLite を使用するようになっています）。
- .env は機密情報を含むため、生成スクリプトのヘッダに「.env を Git にコミットしない」旨を明記しています。config_setup により対話的にシークレットを扱えるようになっていますが、実運用では環境変数管理ツールの利用を検討してください。
- DuckDB / PyYAML など外部ライブラリへの依存はオプションで、存在しない場合は該当チェックや機能がスキップされる設計です（validate_config の YAML チェック等）。

今後の予定（候補）
- research/factor_research の完全実装（ファイル末尾に計算ロジック続きあり）
- strategy や execution の更なるテスト・モジュール化、銘柄ごとの lot_size 対応拡張
- ログ周りのリモート集約（ELK / Loki 等）やメトリクス出力の追加

---