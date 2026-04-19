CHANGELOG
=========

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース (バージョン 0.1.0)。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db 既定）を使用し、MockBrokerClient を利用する設計。
    - プロセス優先度を高く設定し（set_process_priority("high")）、エンジンを別スレッドで起動、停止フラグ（data/stop_requested.flag）を監視して安全に停止できる実装。
    - Engine の PID ファイル出力サポート（data/execution.pid を既定）。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（既定 60 秒）。不正な値は警告して既定値にフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨を明示。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、例外時はログ出力の上で次回ポーリングへ継続。
- 設定管理
  - config.py: 環境変数の読み込み/管理を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、そこから .env/.env.local を自動ロード（任意で無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パーサーは export 形式・クォート文字列・インラインコメント等に対処する堅牢な実装。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、紙取引用 DB パス、閾値設定、環境種別チェックなど）をプロパティ経由で取得可能。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - グローバルインスタンス settings を提供。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 秘匿項目はマスク表示、デフォルト/既存値を再利用できるインタラクティブ UX。
    - .env ファイルの書式テンプレートを出力。
  - validate_config.py: 起動前設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML がなければパース検証をスキップして警告）等を実施。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio モジュールを追加:
    - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
    - risk_adjustment.py: セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を実装。未知レジーム時はフォールバック挙動とログ警告を行う。
    - position_sizing.py: 発注株数決定ロジックを実装（allocation_method: "risk_based"/"equal"/"score" 対応）。単元株丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積もり、残差配分ロジック等を実装。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを実装。
    - stdout（StreamHandler）出力と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を定義。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定および CPU affinity 設定を実装。
    - Windows / POSIX (Linux, macOS, FreeBSD) を吸収し、アクセス権限不足等の場合は警告してスキップする堅牢な実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート出力ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う。各種閾値（稼働率 99% 等）を定義。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db) をサポート。DB が存在しない場合にエラーメッセージを出力。
- 研究用モジュール
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum/Value/Volatility/Liquidity の設計に基づく）。
    - DuckDB 接続受け取り、prices_daily/raw_financials テーブル参照の設計。モメンタム関連定数と P95 等のユーティリティを実装。calc_momentum の実装開始（ファイル途中での実装分あり）。
- パッケージ
  - __init__.py にてバージョンを __version__ = "0.1.0" に設定。

Changed
- なし（初回公開のため主に追加のみ）。

Fixed
- なし（初回公開）。

Notes / 実装上の注意
- run_monitoring は Monitoring 用 DB として settings.sqlite_path（監視 DB）を環境に依らず使用する設計。paper_trading と execution の DB 分離は run_execution 側で制御している。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority の機能は OS と権限に依存します。権限不足や未対応 OS の場合は警告が出力され、処理は継続されます。
- position_sizing や risk_adjustment のアルゴリズムは PortfolioConstruction.md / StrategyModel.md 設計に沿った純粋関数実装であり、将来的に lot_size の銘柄毎対応や価格フォールバックなどの拡張を想定した TODO コメントがあります。
- research/factor_research.py は一部実装が途中で終わっている箇所があります（今後の追加実装が必要）。

Security
- なし

References
- 各モジュール内の docstring / コメントに詳細な設計意図・利用方法を記載しています。コマンドラインで利用可能なツールはそれぞれ python -m <module> で実行できます（例: python -m kabusys.validate_config, python -m kabusys.config_setup, python -m kabusys.tools.paper_verification_report）。