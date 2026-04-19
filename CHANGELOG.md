CHANGELOG
=========

すべての notable な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠し、語調は日本語です。

[Unreleased]

[0.1.0] - 2026-04-19
--------------------

Added
- 基本構成・エントリポイントを実装（初回リリース）。
  - パッケージバージョン: 0.1.0
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルト構成値を設定（max_position_pct, max_utilization, rate_limit_per_sec 等）し、initial_portfolio_value を broker.get_available_cash() から初期化。
    - ExecutionEngine をデーモンスレッドで実行。data/stop_requested.flag を検知したらエンジンを停止。
    - 実行時に PID ファイルを data/execution.pid に書き出す（設定により変更可能）。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループを追加。起動時にプロセス優先度を "high" に設定。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - data/stop_requested.flag の検知でループを正常終了。KeyboardInterrupt をハンドリングしてクリーンに終了。
- 設定関連
  - config.py
    - 環境変数管理クラス Settings を実装。J-Quants / kabu API / DB パス /監視閾値 /ログレベル等をプロパティ経由で取得。
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。優先度: OS 環境 > .env.local > .env。
    - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パース時の細かな挙動:
      - export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメントの扱い（クォート有り無しで差異あり）。
    - PAPER_FILL_MODE の検証（instant / partial / never / reject のみ有効）等、各種バリデーションを実装。
  - config_setup.py
    - 対話式 .env ウィザードを追加。主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話で作成・更新可能。
    - 既存 .env の読み込み、シークレット値のマスク表示、保存前確認を実装。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数チェック (.env 未設定やプレースホルダ値検出)、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実行。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START の危険な設定検出）。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定を提供。ルートロガーをクリアしてから StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > INFO。ログディレクトリ解決順: 引数 > LOG_DIR 環境変数 > logs/（デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム（Windows / POSIX）差分を吸収してプロセス優先度を設定するユーティリティを実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n)（最初の n コアに固定）を提供。アクセス権限や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選択（同点は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3、未知は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" | "equal" | "score") に応じた発注株数計算を実装。lot_size 単位で丸め、per-stock 上限・aggregate cap（available_cash を超えた場合のスケールダウン）を考慮。cost_buffer により保守的なコスト見積りを適用。price 欠損時はスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計してレポート出力。
    - 判定基準（閾値）を定義し、PASS/FAIL を出力:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ (--from, --to) と --db オプションを提供。DB テーブルが存在しない場合は安全にデフォルト値を使用。
- research/factor_research.py
  - ファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity を算出する方針を実装（関数や定数定義あり。詳細実装は継続開発予定）。

Changed
- 初期設計としてプロセス優先度を起動スクリプトの最初で high に設定するように統一。
- ロギング: コンソールは stdout を使用（stderr ではない） — タスクスケジューラや cron とリダイレクトを一本化する運用上の配慮。

Fixed
- .env パーサーの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等を正しく処理するよう改善。
- validate_config で YAML 未インストール時にも警告を出してスキップするようにした（パッケージの有無に依存しない実行性向上）。

Security
- .env を生成する際の注意喚起（.env を絶対に Git にコミットしないこと）を config_setup.py の生成ヘッダに記載。

Notes / Known limitations
- research/factor_research.py はファクター計算ロジックの主要部分が継続開発中（ファイル末尾で処理が途中の状態が見られる可能性があります）。
- position_sizing の価格欠損時は当該銘柄をスキップするため、欠損価格が多いと実際の配分が想定と異なることがあり得ます（TODO コメントでフォールバック価格の導入を検討）。
- process_priority の設定はプラットフォームや権限に依存し、AccessDenied 等が発生した場合は警告し設定をスキップします。
- run_monitoring は監視 DB に本番の sqlite_path を常に使用する仕様のため、開発・検証用途で分離したい場合は環境を適切に構成してください。

開発者向けメモ
- エントリポイント:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report
- 主要環境変数の例:
  - KABUSYS_ENV (development | paper_trading | live)
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
  - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE

-- end --