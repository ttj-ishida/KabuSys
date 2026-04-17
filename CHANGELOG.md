Changelog
=========
すべての注目すべき変更をここに記録します。慣例に従いセマンティックバージョニングを採用しています。

フォーマット: Keep a Changelog 準拠

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージ初期実装。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 設定 / 環境変数管理
  - Settings クラスを導入し、環境変数からアプリ設定を取得可能に (src/kabusys/config.py)。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml、.env → .env.local の順）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーは export 形式、シングル/ダブルクォート、インラインコメント、エスケープをサポート。
  - 設定値にはデフォルトやバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
- 設定関連 CLI
  - 対話式 .env 作成ウィザード (config_setup.py) を追加。既存 .env 読み込み、秘密値のマスク表示、保存テンプレート出力をサポート。
  - 設定検証 CLI (validate_config.py) を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパースを検証。--strict モードで警告を失敗扱いにできる。
- 実行コンポーネント起動スクリプト
  - ExecutionEngine 起動スクリプト (run_execution.py) を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite に分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory により本番/モックブローカークライアントを選択。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine.run_session をデーモンスレッドで実行。data/execution.pid を使用。
    - 停止は data/stop_requested.flag により検知してエンジンを停止。
  - SystemMonitor 起動スクリプト (run_monitoring.py) を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは production DB を想定）。
    - stop フラグ検知でループ終了、例外はログ出力してポーリングを継続。
- モニタリング DB 初期化
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- Paper Trading 検証ツール
  - paper_verification_report.py を追加。
    - ペーパートレード用 SQLite（環境変数/PAPER_TRADING_SQLITE_PATH または --db 指定）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）を算出、閾値判定して PASS/FAIL レポートを標準出力に出力。
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。
- ポートフォリオ構築ライブラリ
  - portfolio モジュールを実装。
    - select_candidates: スコア降順・タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
    - calc_position_sizes: risk_based / equal / score の割当方法、単元株（lot_size=100）で丸め、aggregate cap と cost_buffer によるスケールダウンロジックを実装。
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター比率が上限を超える場合、新規候補から除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market regime に応じた投下乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告して 1.0 フォールバック）。
- リサーチ / ファクター計算
  - factor_research.py を追加（DuckDB 接続を使用）。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20）、流動性指標等を prices_daily テーブルから計算する関数を実装。
    - DuckDB SQL を用いたウィンドウ集計で営業日ベースのラグを計算。
- ユーティリティ
  - process_priority.py を実装。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップする。
- DB 接続
  - 実行スクリプトで sqlite3 と duckdb の両方を接続して利用する構成を採用。

Changed
- n/a（初回リリースのため変更履歴なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Notes / 制限事項
- 権限と互換性
  - プロセス優先度や CPU affinity の設定は実行ユーザーの権限やプラットフォームに依存し、失敗時は警告を出してスキップする実装になっています。
- 価格欠損時の処理
  - apply_sector_cap / calc_position_sizes の一部ロジックで価格が欠損 (0.0) の場合に誤ったエクスポージャー/割当になる可能性があります。price のフォールバック（前日終値や取得原価）を将来導入する TODO をコメントで残しています。
- P95 の算出
  - paper_verification_report の P95 計算はサンプル多数に対して専用ロジックで計算しており、空データは N/A を返します。
- .env の取り扱い
  - config_setup による .env ファイルはセキュリティ上 Git へコミットしないことを明示。
- monitoring と実行 DB の分離ポリシー
  - 監視コンポーネントは KABUSYS_ENV に依存せず監視用 SQLite（Settings.sqlite_path）を使用します。一方、ExecutionEngine は paper_trading の場合に paper_sqlite_path を使用してデータを完全に分離します。
- 互換性
  - YAML パースを行う validate_config は PyYAML が未インストールの場合に YAML 検証をスキップして警告を出します。

Usage highlights
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視モニタ起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

開発者向け補足
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- 設定の必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config で検出されます）。
- ログレベルや閾値は環境変数で調整可能（LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT 等）。

例: 主要環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- PAPER_TRADING_SQLITE_PATH: paper trading 用 DB（paper_trading の場合に使用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパス

[0.1.0]: 初回リリース（2026-04-17）