CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
Semantic Versioning を想定しています。

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-18
-----------------

初回公開リリース。以下の主要機能・改善・実装を含みます。

Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: .env ファイルおよび環境変数からの設定読み込みを実装（自動ロード機能、.env/.env.local の優先度、OS 環境変数保護）。
  - Settings クラスを提供し、J-Quants / kabu API / データベース / 監視しきい値 / システム設定等のプロパティを安全に取得可能。
  - .env パースの堅牢化: export プレフィックス対応、クォート内エスケープ対応、インラインコメント処理など。
- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を生成・更新するユーティリティを追加（シークレット入力のマスク表示、デフォルト値・選択肢のサポート）。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML 未導入時はスキップして警告）。
- ロギングと運用ユーティリティ
  - utils/logging_setup.py: 全起動スクリプトで共通利用するログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を自動的に無効化し、コンソール出力へフォールバック。
  - utils/process_priority.py: psutil を用いたプロセス優先度（Windows の priority class / POSIX の nice）および CPU affinity 設定ユーティリティを追加。対応外 OS や権限不足時は警告を出し安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。calc_score_weights は全スコアが 0 の場合に等重配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限適用関数 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を追加。未知レジーム時はフォールバックと警告。
  - portfolio/position_sizing.py: 発注株数算出（risk_based / equal / score）と aggregate cap スケーリング、単元（lot_size）での切り捨て・再配分ロジックを実装。cost_buffer を用いた保守的コスト見積りに対応。
  - package-level exports を提供（kabusys.portfolio）で簡単に利用可能に。
- Execution 内部コンポーネント組み立て（起動スクリプト側）
  - run_execution.py で BrokerClientFactory によるブローカクライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て・起動を行う。
  - RiskManager のデフォルト構成値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を明示的に設定。initial_portfolio_value は broker.get_available_cash() を利用。
  - ExecutionEngine は別スレッドで run_session を実行し、stop flag の検出で安全に停止する仕組みを提供。
- 監視機能関連
  - run_monitoring.py は SystemMonitor.check_once() を定期実行。停止フラグ（data/stop_requested.flag）や KeyboardInterrupt を処理。DB 初期化（init_monitoring_db）を行う。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を読み取り、稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）等を集計してレポート出力する CLI を追加。P95 計算、日付フィルタ、閾値判定（稼働率 99% 等）を実装。DB 未存在時やテーブル欠損時の堅牢なハンドリングを提供。
- research モジュール開始
  - research/factor_research.py: DuckDB 接続を受けるファクター計算モジュールの骨格を追加（モメンタム等の計算方針と定数を定義）。（実装途中の箇所あり）

Changed
- n/a（初回リリース）

Fixed
- ログ設定・プロセス制御等の失敗耐性を強化
  - logging_setup: ログディレクトリ作成失敗時はファイルハンドラ生成をスキップし、stderr ではなく stdout へコンソール出力を行うように変更（cron 等からの起動を想定）。
  - process_priority: psutil による権限不足・未実装 API 呼び出しを例外として扱わず警告出力でスキップ。

Security
- .env を Git にコミットしないようウィザードに注意書きを追加（config_setup.py）。シークレット項目は表示時にマスク。

Notes / Implementation details
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、見つからない場合は自動ロードをスキップする設計。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Settings は KABUSYS_ENV, LOG_LEVEL 等の値検証を行い、不正値は ValueError で明示的に通知する。
- run_monitoring は監視用 DB を環境に関わらず本番 sqlite_path を用いる設計意図がコメントに記されている（運用上の注意点）。
- run_execution は paper_trading モード時に専用 SQLite を使うことで本番データとの分離を保証。
- いくつかのモジュール（research/factor_research.py 等）は実装途中の箇所が存在する。将来的な拡張で完全実装を行う予定。

今後の予定（短期）
- research/factor_research の完全実装（DuckDB SQL によるファクター集計）
- SystemMonitor / ExecutionEngine 周りのユニットテスト強化とリファクタ
- ブローカクライアントのモック仕様の明文化・テストカバレッジ向上
- 各種設定ファイル（config/*.yaml）テンプレート生成スクリプトの整備

-----------------------------------------------------------------------------
（注）上記はソースコードの内容から推測して作成した CHANGELOG です。実際のコミット履歴やチケット管理に基づく履歴とは差異が生じる可能性があります。必要に応じて日付・詳細を修正してください。