CHANGELOG
=========

すべての重要な変更はここに記録します。本ファイルは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠します。

フォーマット:
- Unreleased: 開発中の変更（存在しない場合は空）
- 各リリースはバージョンと日付を付与

Unreleased
----------
- 現時点で未リリースの小修正・拡張（.env パーサの追加仕様対応や factor_research の続き等）が進行中。

0.1.0 - 2026-04-24
------------------
Added
- 基本コアおよび CLI / ツール群を追加
  - 起動スクリプト:
    - run_execution.py: ExecutionEngine 起動用スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。停止フラグ（data/stop_requested.flag）の検出と PID ファイル（data/execution.pid）連携に対応。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照する実装。
  - 設定/環境系ユーティリティ:
    - config.py: 環境変数/設定管理クラス Settings を追加。.env 自動読み込み（.env / .env.local）・保護された OS 環境変数扱い・各種プロパティ（DUCKDB_PATH/SQLITE_PATH/PAPER_FILL_MODE/kill_flag 等）を提供。
    - config_setup.py: .env 作成・更新を対話式に支援するウィザード CLI を追加。
    - validate_config.py: .env および config/*.yaml の検証 CLI を追加（--strict オプションで警告を FAIL 扱い）。
  - ログ / プロセス制御:
    - utils/logging_setup.py: 統一的なログ設定ユーティリティ（stdout への StreamHandler + 日次ローテーションの TimedRotatingFileHandler）を追加。ログディレクトリ作成失敗時はファイル出力をスキップして警告表示。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定 / CPU affinity ユーティリティを追加（Windows/Linux/Mac の差分吸収、権限不足時は警告でスキップ）。
  - ポートフォリオ構築（純関数群）:
    - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
    - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を追加。
    - portfolio/position_sizing.py: 単元丸め・リスクベース / 等配分の各種発注株数算出 calc_position_sizes を追加（aggregate cap、cost_buffer、lot_size 対応）。
  - 分析 / レポート:
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシなどを算出し PASS/FAIL 判定を行う。閾値（稼働率 99%、成立率 90% 等）はソース内に定義。
  - リサーチ:
    - research/factor_research.py: ファクター計算モジュールを追加（モメンタム等の計算を行う関数を実装開始。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計）。
  - パッケージ初期化:
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- .env 自動読み込みの挙動を明確化
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - .env.local は .env の上書き（override=True）として扱い、OS 環境変数は保護される
- ロギングの動作
  - ログ出力は標準出力（stdout）を使用するように統一（cron / Task Scheduler でのリダイレクト運用を想定）
  - 日次ローテーションをデフォルトで有効化（30日分保持）
- run_monitoring/run_execution の起動シーケンス
  - 最初にプロセス優先度を high に設定するように統一
  - 停止制御はファイル存在確認（stop_requested.flag）で行うように実装

Fixed
- 環境ファイルパーサの堅牢化
  - config._parse_env_line() にて:
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - クォート無しの値に対するインラインコメント処理を改善（# の直前がスペース/タブの場合をコメントと認識）
  - _load_env_file() でファイル読み込み失敗時に warnings.warn を発行して安全にスキップ
- validate_config の検証
  - 必須環境変数が未設定・プレースホルダのまま・KABUSYS_ENV の不正値などを検出し、INFO/WARNING/ERROR を出力するように実装
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出力

Security
- 秘密情報ハンドリングの配慮
  - config_setup の対話表示ではシークレット値（J-Quants トークン、kabu API パスワード、LINE トークン）をマスクして表示
  - .env のサンプル生成時に「.env を絶対に Git にコミットしないこと」を明示

Notes / Known limitations
- run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」仕様。テスト用にモニタリング DB を分離したい場合は別途設定が必要。
- PAPER_FILL_MODE の値検証を Settings で行う（instant/partial/never/reject のみ許容）。不正値は ValueError を発生させる。
- position_sizing の lot_size は現状グローバル共通 (デフォルト 100)。将来的に銘柄別単元対応の拡張が想定されている（TODO コメントあり）。
- research/factor_research モジュールは計算のための SQL 範囲・定数を定義しており、いくつかの関数は実装続行中（例: calc_momentum の末尾が継続される想定）。

Acknowledgments
- このリリースは複数のユーティリティ（環境読み込み、ログ、プロセス優先度）、運用用スクリプト（実行・監視）、ポートフォリオ構築ロジック、および検証/ウィザード・ツール群を初期実装したものです。今後、各モジュールのテスト追加・ドキュメント整備・エラーハンドリング改善を予定しています。