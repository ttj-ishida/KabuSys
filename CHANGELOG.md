CHANGELOG.md
=============
（Keep a Changelog 準拠、重要な変更を時系列で記載。日本語）

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-19
-------------------

Added
- プロジェクト初回公開リリース。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して data/paper_trading.db に完全分離して記録する。停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用。
- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）、環境変数取得用 Settings クラス（各種パス・フラグ・閾値・env 判定プロパティを提供）。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在・パースチェック、--strict オプション（警告を FAIL 扱い）に対応。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 未参照）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算（calc_position_sizes）。lot_size 単位丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りなどを実装。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーを統一的に設定するユーティリティ。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、LOG_DIR の作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- 監視・モニタリング
  - monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。SystemMonitor を利用した定期チェックの流れを確立。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定。日付レンジ指定と DB パス指定 (--db / 環境変数) に対応。
- research
  - research/factor_research.py: ファクター計算モジュールの初期実装（モメンタム、MA200、ATR、出来高系などを想定）。DuckDB を用いた prices_daily / raw_financials の参照を想定した設計。

Changed
- ログ出力の標準化: stdout を StreamHandler に使うことで cron 等からのリダイレクト運用を想定。
- .env 読み込み順序: OS 環境 > .env.local > .env（既存 OS 環境は protected として上書き防止）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- run_monitoring の挙動: 監視は KABUSYS_ENV に依存せず sqlite_path（本番向け）を使用する設計に明示。

Fixed / Improved
- .env パーサーの強化（config.py）
  - export KEY=val 形式に対応。
  - シングル/ダブルクォートを含む値のバックスラッシュエスケープ処理と閉じクォート探索に対応。
  - クォートなし値のインラインコメント処理をスペース/タブの直前判定で実装。
  - 読み込み失敗時は警告を出す（テストや権限問題を考慮）。
- validate_config の堅牢化
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
  - config/*.yaml の存在/パースチェックを実装し、問題を一覧表示する。
- calc_score_weights のフォールバック: 全銘柄のスコア合計が 0 の場合は等金額配分へフォールバックし警告を出力。
- calc_position_sizes のスケーリングロジック: aggregate cap 超過時に比例スケールおよび lot_size 単位での残余配分を行うことで再現性のある割当てを実現。
- process_priority の安全性向上: 未対応プラットフォームや権限不足時に例外を握り潰して警告を出す設計。

Notes / Breaking changes
- run_monitoring は監視用 DB に常に sqlite_path（Settings.sqlite_path）を使うため、開発環境等で期待する DB を使わせたい場合は sqlite_path を環境変数で明示的に切り替えてください。
- Papers trading の発注実行は paper_trading モードで DB を分離しているため、実運用での DB 混同を避ける設計となっています。環境変数（KABUSYS_ENV）と PAPER_TRADING_SQLITE_PATH の設定に注意してください。

Acknowledgements
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートや公開履歴とは異なる可能性があります。追加の履歴や日付、作者情報があれば反映します。