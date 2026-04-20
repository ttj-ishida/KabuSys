CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
重要: 日付はコード確認日（2026-04-20）を使用しています。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-20
-------------------

Added
- 実行エントリポイントを追加 / 実装
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて Paper Trading 時は専用の SQLite（data/paper_trading.db など）を使用し、本番 DB と明確に分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全に終了する。
- 設定管理と初期化
  - config.py: .env 自動読み込み機能（.env / .env.local）をプロジェクトルートから行う実装。環境変数取得用 Settings クラスを提供し、多数のプロパティ（DBパス、APIトークン、Paper Trading 用設定、監視閾値など）を定義。必須変数未設定時の _require() による早期エラーを実装。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加（秘密値はマスク表示）。.env のテンプレート書き出し機能あり。
  - validate_config.py: 起動前に .env や config/*.yaml の検証を行う CLI を追加（--strict モードで警告も失敗扱い）。
- Portfolio / Positioning
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークロジック）、等重み・スコア重み計算を実装。スコア合計がゼロの場合のフォールバックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックと警告を追加。
  - portfolio/position_sizing.py: 各配分方式（risk_based / equal / score）に基づく発注株数算出ロジックを実装。単元株丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer の考慮、残差処理による追加配分ロジックを実装。
  - portfolio/__init__.py: 上記機能を公開するパッケージ化。
- Research
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性等の設計と定数を定義）。DuckDB 接続を利用して prices_daily / raw_financials を参照する想定。モジュール実装を開始（calc_momentum の実装途中まで確認）。
- Monitoring / Observability
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを run_execution/run_monitoring から行い、監視テーブルの存在を保証（冪等）。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し、閾値（稼働率99%、成功率90% 等）に基づいて PASS/FAIL 判定を出力。
- Utilities
  - utils/logging_setup.py: ルートロガーに対する共通ロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップする安全処理を実装。
  - utils/process_priority.py: Windows/Linux/Mac の差分を吸収してカレントプロセスの優先度（high/normal/low）と CPU affinity を設定するユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップする堅牢化を行った。
- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を設定。

Changed
- .env パーサー強化
  - config._parse_env_line: export プレフィクス対応、クォート内エスケープ処理、行内コメントの扱いの厳密化を実装。より実用的な .env パースを提供。
- .env 自動ロード挙動
  - OS 環境変数は保護しつつ .env/.env.local の読み込み順（.env → .env.local、.env.local は override=True）で適用する実装に変更。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。

Fixed
- 環境変数の妥当性チェックとフォールバック
  - run_monitoring._get_poll_interval(): MONITOR_POLL_INTERVAL の不正値（非数値・0以下）に対してロギングで警告しデフォルト（60秒）へフォールバックするように修正。
  - Settings.paper_fill_mode: PAPER_FILL_MODE の有効値チェックを実装し、不正値の場合は ValueError を発生させるようにした。
- 安全なファイル・ディレクトリ操作
  - logging_setup: ログディレクトリ作成に失敗してもコンソールログのみで処理継続する耐障害処理を追加。
  - process_priority / set_cpu_affinity: 権限不足や未対応機能に対して例外吸収と警告出力を実装。

Security
- config_setup にて生成される .env テンプレートで
  - 「.env は絶対に Git にコミットしないこと」の注記を追加し、秘密情報取り扱いに関するガイダンスを明示。
  - 対話ウィザード中に秘密値（トークン／パスワード）はマスク表示することで画面上での露出を抑制。

Notes / Behavior
- 監視モードの DB: run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用する意図で実装されています（監視データは本番データ構造を想定）。
- 実行モードの DB: run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する。
- 停止フラグ / PID
  - run_execution/run_monitoring はプロジェクト内 data ディレクトリの stop_requested.flag を監視し、検知時に安全に終了する設計。Execution は PID ファイル（data/execution.pid）を使用する。
- DuckDB と SQLite を併用
  - 分析用に DuckDB（settings.duckdb_path）を、監視・操作履歴に SQLite（settings.sqlite_path / paper_sqlite_path）を使用する構成を採用。
- Paper Trading
  - Paper Trading 用の検証ツール（paper_verification_report）で P95 計算や各種閾値判定を行う。DB が存在しない場合はエラーメッセージを出力。

Known limitations / TODO
- research/factor_research.calc_momentum は実装途中（ファイルの末尾で切れている状態）で、完全実装は今後の課題。
- position_sizing: 銘柄ごとの lot_size を将来の拡張ポイントとして TODO コメントあり（現状は全銘柄共通の単元を想定）。
- apply_sector_cap: price が欠損（0.0）時のエクスポージャー過少見積りに関する注意点がコメントで記載されており、フォールバック価格取得の拡張が検討中。

Contributors
- 初期実装（ファイル群の追加・初期設計）：コードベースより推測して記載

License
- 本リリースではライセンス表記はソースに明示されていません。プロジェクトルートのライセンスファイルを参照してください。

-----------
（以上）