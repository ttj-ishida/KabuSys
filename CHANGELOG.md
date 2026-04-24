CHANGELOG
=========

すべての重要な変更を追跡します。フォーマットは "Keep a Changelog" に準拠しています。
リリース日付はリポジトリ内のバージョン情報・コードから推定しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージバージョン: __version__ = 0.1.0
- 起動スクリプト / 実行用エントリ
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB (data/paper_trading.db または PAPER_TRADING_SQLITE_PATH) を用いるよう実装。
    - ブローカークライアントのファクトリ (BrokerClientFactory) を使用し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立て実行する。
    - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) を利用して安全に停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは本番 DB を前提）。
    - 停止フラグ検出でループを安全終了。
- 設定関連ツール
  - config_setup.py: 対話式 .env ウィザードを追加。
    - .env の初期作成・更新を支援。各項目の説明・既存値の再利用・シークレット表示（マスク）に対応。
    - 出力ファイルに注意書き（.env を Git にコミットしない等）を含む。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数やパス、config/*.yaml の存在・YAML パース（PyYAML 利用可能時）をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - 稼働率、注文成功率・送信率、レイテンシ（avg/max/P95）、リスク却下数などを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで上書き可能。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルから候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を追加。
  - portfolio/position_sizing.py
    - 発注株数決定ロジックを実装。risk_based / equal / score の配分方式、単元株丸め、最大ポジション上限、aggregate cap によるスケールダウン処理を含む。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一的セットアップ関数を追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR によるカスタマイズ対応、ファイルハンドラ作成失敗時のフォールバックあり。
  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows/Linux(Mac含むPOSIX) の違いを吸収。
    - 優先度 ("high" / "normal" / "low") を指定可能。権限不足時は警告でスキップ。
- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートに .git または pyproject.toml がある場合）。
    - export KEY=val、クォート、エスケープ、インラインコメントなどに対応した .env パーサーを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能（テスト用途）。
    - Settings クラスで環境変数をプロパティ経由で取得。値検証（enum や閾値）、デフォルト値の定義を提供。
    - 新しい/重要な環境変数:
      - PAPER_FILL_MODE（instant/partial/never/reject）
      - PAPER_TRADING_SQLITE_PATH
      - MONITOR_POLL_INTERVAL（run_monitoring側で使用）
      - KILL_FLAG_CLEAR_ON_START
      - DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LOG_DIR など
- データ・分析
  - research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム等のフェーズ実装を想定）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。

Changed
- ロギングのデフォルト運用方針を明確化
  - stdout をコンソール出力に利用（stderr ではない）。cron 等での出力統一を考慮。
  - 日次ログローテーション・30日保持をデフォルトに設定。
- DB 接続方針
  - 監視（monitoring）は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様を明確化（監視データは一元化）。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用し、本番 DB と完全分離する。

Fixed
- .env パースの堅牢化
  - export プレフィックス、クォート内のエスケープ、コメントの扱いなどを改善し、実運用での .env 設定読み込みに耐えるように修正。
- ポジションサイズ算出のスケーリングロジック
  - aggregate cap 適用時のスケーリングと端数処理（lot_size 単位での配分）を実装し、残余キャッシュを考慮して再配分することで合計コストが available_cash を超えにくくした。

Security
- シークレットの扱い
  - config_setup の対話ではシークレット項目をマスク表示。README/出力コメントで .env を Git にコミットしない旨を明示。

Notes / Known limitations
- research/factor_research.calc_momentum 等、ファクター計算モジュールは DuckDB のテーブル構造（prices_daily / raw_financials）を前提としているため、実データ準備が必要。
- process_priority の設定は権限に依存し、権限不足時はログで警告を出して操作をスキップする設計。
- monitoring で用いる sqlite DB は本番 DB（settings.sqlite_path）を使用するため、ローカル開発で監視データを分離したい場合は運用上の注意が必要（環境変数で sqlite_path を切り替えるなど）。

参考: 主なコマンド
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

----------------------------------------
この CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時は変更履歴やコミットログを参照して補完してください。