CHANGELOG
=========

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

Added
- 初回リリース。以下の主要機能・モジュールを追加。
  - CLI / 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト。環境変数 KABUSYS_ENV に応じて本番/ペーパートレードを切り替え、ペーパートレード時は専用 SQLite（data/paper_trading.db）に記録。停止用フラグファイル監視、PID ファイル出力、スレッドでのエンジン実行管理を実装。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）、停止フラグの検知処理を実装。
  - 環境設定関連
    - config.py: .env / .env.local の自動読み込み機能（プロジェクトルート検出）、高度な .env パーサ（export 形式・クォートやエスケープの扱い・インラインコメント対応）、Settings クラス（各種環境変数のプロパティ化とバリデーション）を実装。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツール。必須項目・説明・デフォルト値・シークレットマスク表示をサポート。
    - validate_config.py: 起動前設定検証ツール。.env と config/*.yaml の検証ロジックを提供（--strict オプションで警告も FAIL 扱い）。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分を提供。スコア全てが 0 の場合のフォールバックロジックあり。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（既存ポジションのセクター比率を計算して新規候補を除外）、市場レジームに応じた投下資金乗数の計算（bull/neutral/bear マップ）を実装。
    - portfolio/position_sizing.py: 各銘柄の発注株数決定ロジック（risk_based / equal / score）、単元株丸め、ポジション上限・aggregate cap（available_cash によるスケールダウン）、手数料・スリッページ想定（cost_buffer）を実装。
  - リサーチ/ファクター計算
    - research/factor_research.py: DuckDB を用いたファクター計算（Momentum: 1M/3M/6M リターン、MA200 乖離、Volatility: ATR20、出来高/売買代金指標など）を実装。prices_daily / raw_financials テーブルのみ参照する設計。
  - 監視・検証ツール
    - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析して検証レポートを生成するツール。稼働率・注文成功率・送信率・P95 レイテンシなどを計算し PASS/FAIL を判定する閾値を定義。
  - ユーティリティ
    - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows/Linux/macOS 対応）、CPU affinity 設定関数を提供。psutil の例外をハンドルして安全にフォールバック。

Changed
- n/a（初回リリースのため過去バージョンとの差分なし）

Fixed
- 設定の堅牢化・安全弁の追加
  - run_monitoring.py: MONITOR_POLL_INTERVAL の値が不正（0 以下や非整数）の場合にデフォルトへフォールバックし、警告ログを出力するようにした（time.sleep に渡す誤値対策）。
  - config.py: PAPER_FILL_MODE の許容値検証とエラーメッセージを実装（無効値時は ValueError）。
  - process_priority.py: 未対応 OS や権限不足時に警告ログを出して処理をスキップするようにし、例外で中断しないように改良。
  - run_execution.py/run_monitoring.py: 停止フラグ（data/stop_requested.flag）検知により安全にシャットダウンする仕組みを追加。

Deprecated
- n/a

Removed
- n/a

Security
- config_setup.py に .env を絶対にコミットしない旨の注記を追加（README 等への誘導）。環境変数はシークレット扱いの項目はマスク表示。

Notes / Implementation details
- DB 分離: ペーパートレード環境は本番 DB と完全に分離する設計（Settings.paper_sqlite_path を利用）。監視用 DB は環境に関わらず本番 sqlite_path を使用する仕様に注意。
- DuckDB: 分析用に DuckDB を採用。research/factor_research.py と一部起動処理で DuckDB 接続を利用。
- ログと CLI: 各種スクリプトは logging.basicConfig(level=logging.INFO) を使用しているため環境変数 LOG_LEVEL による制御を想定（Settings.log_level でバリデーションあり）。
- 未実装/注意事項: 一部 TODO コメント（例: price のフォールバック、lot_size の銘柄別対応）が残っており、将来的な改善点が明示されています。

開発者向け情報
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" を参照してください。