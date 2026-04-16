CHANGELOG
=========

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-16
--------------------

初回公開リリース。以下の主要コンポーネントと機能を実装しています。

Added
- 基本情報
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として公開。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視データは環境にかかわらず本番用 sqlite_path を使用する（監視テーブルは起動時に初期化）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
    - プロセス優先度を High に設定して起動（utils.process_priority を使用）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。
    - 停止フラグ（data/stop_requested.flag）検知で Engine を停止。
    - PID ファイル管理（data/execution.pid）に対応。
    - プロセス優先度を High に設定。

- 設定管理
  - config.Settings クラスを実装
    - 環境変数／.env ファイルからの設定取得。
    - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサーの実装（export プレフィックス・クォート・インラインコメント等に対応）。
    - 各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、監視閾値（CPU/MEM/DISK）、KABUSYS_ENV 検証（development / paper_trading / live）、LOG_LEVEL 検証 等。
    - PAPER_FILL_MODE（instant/partial/never/reject）のバリデーション。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。
    - CPU Affinity 固定用の set_cpu_affinity を実装（None を指定すると何もしない）。
    - 実行権限不足や未サポートプラットフォームでのフォールバック・警告を備える。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順で N 件選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化による配分、全スコアが0のときは等配分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中上限チェック、既存保有を考慮）
    - calc_regime_multiplier（市場レジームに応じた投入資金乗数: bull/neutral/bear のマッピング、未知レジームは警告して 1.0 にフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes（risk_based / equal / score の配分方式に対応、lot_size 単位丸め、aggregate cap によるスケールダウンと残差の分配ロジック、cost_buffer 考慮）

- 研究（Research）モジュール
  - research.factor_research
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比）
    - calc_value（PER、ROE。raw_financials から最新財務情報取得）
    - DuckDB を用いた SQL / ウィンドウ関数ベースでの計算実装
  - research.feature_exploration
    - calc_forward_returns（多ホライズンの将来リターンを一括で計算）
    - calc_ic（スピアマン順位相関による IC 計算）
    - rank（同順位は平均ランクで処理）
    - factor_summary（count/mean/std/min/max/median の統計サマリー）
  - research.__init__ で必要関数をエクスポート（zscore_normalize は data.stats から再利用）

- AI ニュース NLP（OpenAI 連携）
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ格納する処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換ユーティリティを実装。
    - バッチサイズ、文字数制限、記事数制限、スコアクリップ（±1.0）、リトライ（429 / ネットワーク / 5xx に対する指数バックオフ）等の実運用向け堅牢化。
    - 出力 JSON の厳密なバリデーション、部分失敗時に既存スコア保護のため対象コードを限定して差し替える設計。
    - OpenAI API キー未設定時は明確にエラーを返す。
    - 実装においてルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成コマンドを追加（コマンドライン引数 --from / --to / --db 対応）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。
    - データ存在チェック、SQLite テーブル（system_status, trade_logs, risk_logs 等）への頑健なクエリ実装。
    - パス／フェイル基準値を定義（例: 稼働率 >= 99%、P95 <= 200ms など）。
    - P95 計算ユーティリティと表示フォーマットを提供。

Changed
- （初回リリースにつき過去からの変更はなし）

Fixed
- （初回リリースにつき過去からの修正はなし）

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キー等の必須情報は環境変数から供給する設計。キー未設定時は処理を停止して明示的なエラーを出す実装。

Notes / Usage
- 環境変数の自動ロード
  - プロジェクトルートが特定できる場合、自動的に .env（既存値を上書きしない）→ .env.local（上書き）を読み込みます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実行方法（例）
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 監視と実行エンジンの DB 分離
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用。
  - 実行エンジンは KABUSYS_ENV=paper_trading の場合 settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。

その他
- 各モジュールは「DB 参照なしでの純粋関数化」「DuckDB を利用した高速分析」「外部 API との接続は明示的にキーを要求する」など設計方針を明確化しています。
- 実装の詳細（例: lot_size の将来拡張、価格欠損時の TODO）についてはソース内コメントに注記しています。

問い合わせ・貢献
- 問題報告やプルリクエストはリポジトリの Issue / PR を利用してください。