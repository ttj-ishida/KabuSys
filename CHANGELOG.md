CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （今後のリリース用のプレースホルダ）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージ初期リリース。
- 実行/監視関連
  - run_execution: ExecutionEngine 起動スクリプトを追加。以下の機能を提供：
    - KABUSYS_ENV=paper_trading 時は本番 DB とは分離された paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用してペーパートレードが可能。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag を検知すると安全に停止する。
    - 実行中 PID をファイルに出力（data/execution.pid など）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を上げる（set_process_priority("high") を呼び出し）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - monitoring 用 DB テーブルを init_monitoring_db() で初期化（冪等に実行）。
  - DB 接続: DuckDB と SQLite を併用。duckdb_conn を各処理に渡す設計。

- 設定・環境変数管理
  - 設定モジュール (kabusys.config) を追加。
    - プロジェクトルート検出ロジック: __file__ を起点に .git または pyproject.toml を探索してルートを特定（配布後の動作を安定化）。
    - .env / .env.local の自動ロード機能（OS 環境変数の保護、.env.local は上書き許可）。
    - export KEY=val, クォート（シングル/ダブル）、エスケープ、インラインコメントを考慮した .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能（テスト用途）。
    - Settings クラスを導入し、環境依存値をプロパティで提供（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/MEM/DISK 閾値, env/log_level 判定など）。
    - env 値や PAPER_FILL_MODE、LOG_LEVEL のバリデーションを実装（不正な値は ValueError）。

- ポートフォリオ構築・リスク管理
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定、上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分を提供。全スコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ（既存保有のセクター比率を計算、sell_codes を除外して評価）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: weight/candidates/portfolio_value 等を元に発注株数を算出（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、per-position 上限（max_position_pct）や aggregate cap（available_cash）に基づくスケーリングを実装。
    - cost_buffer を考慮した保守的なコスト見積もり、スケールダウン後の残余を fractional remainder に基づき再配分するロジックを実装。
    - リスクベース算出時は stop_loss_pct に基づく position sizing を提供。

- 研究/ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離（MA200）を計算（DuckDB のウィンドウ関数を利用、データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播を正しく扱う）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を計算（target_date 時点の最新財務を取得）。
  - research.feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターンを一回のクエリで取得。horizons の入力検証あり。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク付け、基本統計量の集計を標準ライブラリのみで実装。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - コマンドラインから期間指定 (--from/--to) と DB パス (--db) を受け取る。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計。
    - 判定基準（しきい値）を定義して PASS/FAIL 判定を返却。P95 パーセンタイル計算や各種フォールバック（テーブル未存在時の安全処理）を実装。

- AI / ニュース NLP（下書き実装）
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化するモジュールを追加。
    - ニュース時間ウィンドウ（JST 基準 -> UTC 変換）計算ユーティリティを実装。
    - バッチサイズ、トークン肥大対策（記事数と文字数制限）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、JSON レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の安全な DB 更新戦略（対象コードのみ置換）を設計。
    - OpenAI API キーの解決と未設定時のエラー処理を実装。
    - （注）モジュール末尾が切れているため、一部処理は未完の可能性あり。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: psutil を用いて Windows/POSIX の差分を吸収したプロセス優先度設定ユーティリティを追加（"high"/"normal"/"low"）。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能を追加。権限不足や未対応プラットフォームを考慮して警告でスキップ。
    - 失敗ケースはログ警告でフェイルセーフに扱う。

- パッケージ化
  - kabusys.__init__ に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

Changed
- なし（初回リリース）。

Fixed
- run_monitoring の MONITOR_POLL_INTERVAL のパースに妥当性チェックを追加。不正値は警告してデフォルトにフォールバック（time.sleep の ValueError 回避）。

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / 実装上の注意
- .env パーサは export 構文、クォート、エスケープ、インラインコメント等に対応するが、完全なシェル互換を保証するものではありません。特殊ケースは .env の記述を見直してください。
- ai.news_nlp モジュールは堅牢化の設計がなされている一方で、実行時の OpenAI API レスポンスフォーマット依存やエラー処理の微調整が必要になる可能性があります（未完部分あり）。
- Position sizing / sector cap のロジックは現状共通 lot_size（デフォルト 100）を前提にしています。将来的な拡張（銘柄別 lot_size）のための TODO コメントあり。
- run_monitoring は「環境に関わらず本番 sqlite_path を使用する」点に注意してください（監視とトレード実行の DB 分離は設計次第で調整可能）。

Contributing
- バグ報告・機能要望は ISSUE を立ててください。プルリクはテスト付きで歓迎します。