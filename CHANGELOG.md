CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
日付はリリース日を示します。

[Unreleased]
------------

- なし（次回リリースに向けた変更をここに記載してください）。

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース（v0.1.0）。日本株自動売買システム「KabuSys」の基本機能をまとめて実装。
  - 実行エントリ/運用
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は本番 DB と完全に分離して data/paper_trading.db を使用。
      - BrokerClientFactory により環境に応じた BrokerClient を生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動。
      - EngineConfig により target_date を指定して run_session() を実行。
    - run_monitoring.py: SystemMonitor をポーリングする起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する旨の設計。
    - 両スクリプトとも起動時にプロセス優先度を設定(set_process_priority("high"))する処理を追加。
  - 設定 / 環境管理
    - config.py: 環境変数管理クラス Settings を導入。
      - .env 自動ロード機能（プロジェクトルート判定: .git / pyproject.toml）を追加。
      - .env と .env.local の読み込み順、OS 環境変数保護ロジックを備えた読み込み実装。
      - 多数の設定プロパティを提供（J-Quants, kabu API, LINE, duckdb/sqlite パス, PID/KILL フラグパス, 監視しきい値等）。
      - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）や PAPER_TRADING_SQLITE_PATH 等の明示的プロパティを提供。
  - データ / 分析
    - research パッケージ:
      - factor_research.calc_momentum / calc_volatility / calc_value を追加（DuckDB 経由で prices_daily / raw_financials を参照）。
      - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank を追加（将来リターン・IC/統計解析機能）。
      - research.__init__ で zscore_normalize を含む公開 API を整備。
    - ai/news_nlp.py:
      - raw_news を OpenAI (gpt-4o-mini) に送って銘柄ごとのセンチメントスコアを ai_scores に書き込む機能を追加。
      - バッチ処理、チャンクサイズ、トークン肥大対策（記事数・文字数のトリム）、429/5xx 等のリトライ方針、スコアのクリップ処理を実装。
      - calc_news_window により対象ニュース時間ウィンドウを厳密に計算（JST ⇄ UTC 変換）。
  - ポートフォリオ構築
    - portfolio パッケージ:
      - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコア重みのフォールバック含む）。
      - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに応じた乗数）。
      - position_sizing: calc_position_sizes（risk_based / equal / score の割当、単元株丸め、aggregate cap スケーリング、cost_buffer 対応）。
  - ユーティリティ
    - utils/process_priority.py:
      - マルチプラットフォーム（Windows / POSIX）でのプロセス優先度設定機能を実装。CPU affinity 設定関数も提供。
      - 権限不足や未対応プラットフォーム時は警告ログを出して安全にフォールバック。
  - 運用ツール
    - tools/paper_verification_report.py:
      - Paper Trading 用 SQLite ログから検証レポートを生成する CLI を追加。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標計算と PASS/FAIL 判定を行う。
      - 日付レンジ指定 (--from / --to) と DB パス指定 (--db) に対応。

Changed
- パッケージ初期構成としてモジュールの公開 API を整理（portfolio/__init__.py, research/__init__.py）。
- ロギング出力は各スクリプトで基本設定(level=INFO) を行うよう統一。

Fixed
- 設計段階で考慮されたいくつかのフォールバックと検証ロジックを実装：
  - MONITOR_POLL_INTERVAL の不正値（0 以下や文字列）の扱いは警告を出しデフォルト値にフォールバック。
  - PAPER_FILL_MODE の不正値は ValueError を送出して設定ミスを早期に検出。
  - position_sizing: スコア合計が 0 の場合のフォールバック、価格/lot 単位での丸め、aggregate cap のスケーリング実装。
  - .env 読み込みでのクォート/エスケープ/インラインコメント処理の強化。

Security
- ai/news_nlp: OpenAI API キーは引数/環境変数から取得。未設定時は明示的にエラーを送出して失敗原因を明確化。
- .env 自動読み込み時に OS 環境変数を protected として上書きを防止する仕組みを実装。

Notes / Upgrade
- run_monitoring は「監視用 DB に本番 sqlite_path を常に使用する」設計です。開発環境で監視を動かす場合は SQLITE_PATH を明示的に指定してください。
- Paper Trading 実行時は run_execution が paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用するため本番データと分離されています。
- 環境変数自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を利用する ai/news_nlp の呼び出しは API キーと適切なネットワーク権限が必要です。実運用でのレート制限や API エラーに対する監視・アラートを検討してください。

Released-by
- KabuSys 開発チーム

---- 

（この CHANGELOG はコードベースから推測して作成しています。リリースごとに実際の差分を基に適宜更新してください。）