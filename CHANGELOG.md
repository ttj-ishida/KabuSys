CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットについて: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-23
------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基盤機能を実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用。KABUSYS_ENV=paper_trading 時に MockBroker を利用し paper_trading 用 DB（data/paper_trading.db など）で本番 DB と分離して動作。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検出で安全に終了。
- 設定管理
  - config.py: .env 自動読み込み（.env/.env.local、OS環境変数保護）、環境変数パースの強化（export 形式、クオート、エスケープ、インラインコメント処理）。Settings クラス経由で型変換・バリデーションを提供（env, log_level, paper_fill_mode など）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装（秘密値マスク、選択肢、確認・保存機能）。
  - validate_config.py: 起動前チェック CLI。必須環境変数・ファイル構成・YAML の簡易パース確認・本番環境向けの追加ガードなど。--strict モードをサポート（警告を FAIL 扱い）。
- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定（コンソール stdout と日次ローテーションファイル）を提供。ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバック。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity 設定を提供。アクセス権限やプラットフォーム非対応時の安全なフォールバックを実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選別（スコア降順・タイブレーク）、等重み・スコア加重の計算。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知レジーム時のフォールバックとログ出力を実装。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score）、単元株丸め、ポジション上限・合計キャッシュに基づくスケーリング、コストバッファ対応。端数処理は lot 単位で安定的に配分。
  - portfolio/__init__.py で主要関数を公開。
- モニタリング／監査
  - monitoring モジュールを起動スクリプトから利用する統合（monitoring DB 初期化を行う init_monitoring_db 呼び出し）。
- 解析・リサーチ
  - research/factor_research.py: ファクター計算モジュールの基盤（モメンタム／MA／ATR 等の定数、DuckDB 接続を使った計算方針の実装開始）。（注: ファイル末尾は切れており未完の部分あり）
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計して判定（PASS/FAIL）を出力。期間指定（--from/--to）と DB パスオーバーライド（--db）をサポート。閾値はソース内定数で管理。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリースのため過去バージョンからの変更はなし）

Fixed
- 起動時や I/O エラーに対する堅牢性強化:
  - ログディレクトリ作成失敗時にファイルハンドラ作成をせずコンソール出力のみで継続するように変更。
  - 環境変数読み込み時のファイル I/O エラーは警告を出してスキップ。
  - process priority / CPU affinity 設定で権限不足や非対応環境を捕捉して警告ログを出すように。

Deprecated
- n/a

Removed
- n/a

Security
- n/a

Notes / 実装上の注意
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Paper Trading は本番 DB から分離される設計（PAPER_TRADING_SQLITE_PATH にて上書き可）。PAPER_FILL_MODE により MockBroker の約定挙動を制御（"instant"|"partial"|"never"|"reject"）。
- run_execution と run_monitoring は起動直後にプロセス優先度を "high" に設定しようとするため、権限によっては警告が出る可能性あり。
- research/factor_research.py は途中で切れているため、実運用前に実装完了とテストを要する。

Authors
- プロジェクト内ソースに基づき自動生成（コードベースから推測）。