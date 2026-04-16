CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

フォーマット: 日本語（Keep a Changelog 準拠）

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-16
-----------------

Added
- パッケージ初回リリース（__version__ = 0.1.0）。
- 設定・環境変数管理 (kabusys.config.Settings)
  - プロジェクトルート自動検出（.git / pyproject.toml を基準）に基づく .env 自動ロード機能（.env → .env.local、OS 環境変数保護あり）。
  - .env パーサーは export KEY=val、クォート（シングル/ダブル）やエスケープ、行末コメントの扱いに対応。
  - 必須値チェック (_require)、KABUSYS_ENV / LOG_LEVEL 等の検証、各種パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH など）を Path として提供。
  - PAPER_FILL_MODE の検証（instant, partial, never, reject）等。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - 停止は data/stop_requested.flag を検知して安全に終了。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント選択、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。
    - デフォルトの RiskConfig 値を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - 停止フラグ（data/stop_requested.flag）検知でエンジン停止、実行 pid ファイル管理。

- 監視 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等）。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - コマンドライン引数 --from / --to / --db に対応。
    - DB が存在しない場合やテーブルがない場合の許容ハンドリングを実装（OperationalError をキャッチしてデフォルト値を返す）。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: スコア降順 + signal_rank タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 重み計算（score が全て 0 の場合は等配分にフォールバックして警告）。
  - risk_adjustment
    - apply_sector_cap: 同一セクター集中を防ぐフィルタ（sell_codes を除外して計算、"unknown" セクターは除外適用除外）。
    - calc_regime_multiplier: レジームラベルに基づく投下資金乗数（bull/neutral/bear 対応、未知値は警告を出し 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method=("risk_based" | "equal" | "score") に対応した株数計算を実装。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）・aggregate cap（available_cash）を考慮しスケールダウン処理を実装。
    - cost_buffer による保守的コスト見積り、残差処理（fractional remainder に基づく追加配分）あり。
    - 価格欠損時のスキップとデバッグログ。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB SQL で計算。
    - calc_volatility: ATR20、ATR 比率、平均売買代金、出来高比率を計算（true_range の NULL 伝播制御等を実装）。
    - calc_value: raw_financials から最新の財務データを結合して PER/ROE を計算。
  - feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターンを効率的に取得（ホライズン検証、SQL で一括計算）。
    - calc_ic: スピアマンランク相関（IC）を計算（None / 非有限値除外、3 レコード未満で None を返す）。
    - factor_summary / rank: 基本統計量計算とランク変換実装。
  - research.__init__ で主要関数をエクスポート。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - ニュース収集ウィンドウ計算 calc_news_window を実装（JST ベースの前日15:00～当日08:30 を UTC に変換）。
  - score_news の設計（OpenAI API バッチ送信、最大記事・最大文字数トリム、バッチサイズ、リトライ戦略、レスポンス検証、結果の ai_scores テーブルへの部分置換）を追加。
  - OpenAI の例外（APIConnectionError, APIError, APITimeoutError, RateLimitError）に対応するためのインポートと定数定義。
  - （注）score_news の一部実装がファイル末尾で途切れています（トランケーション）。

- ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority: Windows/Linux/macOS 等の差分を吸収してプロセス優先度（high/normal/low）を設定。権限不足や未対応 OS の場合は警告してスキップ。
  - set_cpu_affinity: 最初の N コアにプロセスを固定する機能（引数検証と例外ハンドリング）。

- DB 接続
  - SQLite（監視・paper_trading 切替）および DuckDB の接続利用を各モジュールで統合。

Changed
-（新規リリースのため該当なし）

Fixed
- .env 読み込みの堅牢性向上（ファイル読み込み失敗時に警告を出してスキップ）。
- ファクター / レポート系でデータ不足時に安全に None やデフォルトを返すように修正（テーブル未存在時の OperationalError キャッチ等）。
- calc_score_weights で全スコア 0 の場合に等配分へフォールバックしてログ出力。

Known issues / Notes
- ai.news_nlp.score_news の実装が途中で途切れている箇所があります（ファイル末尾で中断）。実運用には完全な API 呼び出しループと DB 書き込み処理の実装が必要です。
- position_sizing の price フォールバックは未実装（price が 0 の場合にエクスポージャーが過少見積もられる旨の TODO コメントあり）。将来的に前日終値や取得原価をフォールバックする設計が推奨されています。
- process_priority の権限周りは環境（コンテナ/マネージド環境）に依存するため、警告が出る場合がありますが処理は継続します。
- Paper Trading と本番 DB は明示的に分離されていますが、運用上の混同に注意してください（環境変数で切り替え）。

Security
-（現時点で特筆すべきセキュリティ修正はありません）

Authors
- コードベースから推測して記載しています（実際の作者情報はリポジトリメタデータを参照してください）。

---

この CHANGELOG はコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。補足や修正が必要であれば該当箇所を教えてください。