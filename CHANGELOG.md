CHANGELOG
=========

すべての注目すべき変更点を記録します。
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
--------------


[0.1.0] - 2026-04-17
--------------------
Added
- 基本リリースを追加（パッケージバージョン: 0.1.0）。
- 実行 / 監視用の起動スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine のスレッド起動を行う。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止。
    - PID ファイル管理（data/execution.pid）をサポート。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知でループを終了。KeyboardInterrupt をハンドルしてクリーン終了。
- 設定・環境読み込み
  - src/kabusys/config.py
    - .env/.env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - export KEY=val 形式、クォート内のエスケープ、インラインコメント処理に対応した .env パーサを実装。
    - OS 環境変数を保護する protected ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを導入し、環境変数から各種設定（DB パス、PID ファイルパス、監視しきい値、PAPER_FILL_MODE 等）を取得・バリデーションするプロパティを提供。
- Portfolio（銘柄選定・配分・サイズ計算）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選択、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバックし警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づき新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知はフォールバックと警告）。
    - セクターエクスポージャー計算における価格欠損時の注意点を TODO コメントで明記。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算、単元(lot_size)丸め、per-stock 上限・aggregate cap（available_cash）による縮小ロジックを備える。
    - cost_buffer を含めた保守的コスト見積りと、縮小後の remainder を用いた追加配分処理を実装。
    - 将来的な銘柄別 lot_size 対応は TODO として記載。
  - src/kabusys/portfolio/__init__.py で主要関数をエクスポート。
- 研究/リサーチ機能
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を prices_daily を元に計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を用いて PER/ROE を算出（最新財務レコード選択ロジックを含む）。
    - DuckDB を用いた SQL ベースの効率的な集計実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定 horizon の将来リターンを一括取得。
    - calc_ic / rank: スピアマンランク相関（IC）計算とランク付けユーティリティ（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー実装（None を除外）。
  - src/kabusys/research/__init__.py で主要関数と zscore_normalize を公開。
- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI API (gpt-4o-mini) を用いてセンチメントスコア（-1.0〜1.0）を生成・ai_scores に書き込む設計。
    - バッチ処理（デフォルト 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、JSON モード期待、レスポンスバリデーション、429/ネットワーク/5xx 等に対する指数的バックオフによるリトライを考慮。
    - 日時ウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window を提供。
    - API キー未設定時は ValueError を送出。
    - （注）大きめの処理フローが実装されているが、ファイル末尾で記事取得処理が途切れている箇所があり、実装継続箇所あり（切断により一部欠落している可能性）。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) を吸収して優先度設定を実施。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にピン止め（失敗時は警告）。
  - src/kabusys/utils/__init__.py を追加（パッケージ初期化）。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - SYSTEM/ORDER/RISK/LATENCY 指標を集約し、閾値（稼働率、注文成功率、送信率、P95 レイテンシ）に基づく PASS/FAIL を出力。
    - 日付フィルタ (--from/--to) と --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
    - P95 計算、NULL 安全処理、テーブル未存在時の例外ハンドリングを実装。
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージ名・バージョン・公開サブパッケージ定義を追加（__version__ = "0.1.0"）。

Notes / Known limitations
- src/kabusys/ai/news_nlp.py の末尾で処理が途切れている箇所があり、記事フェッチ部分（_fetch_articles 等）の実装/読み込み完了が必要。現在の実装では一部機能が未完成の可能性あり。
- position_sizing の TODO:
  - price_map に価格欠損がある場合、エクスポージャーが過少見積もられて除外条件が甘くなる点が注記されている（前日終値や取得原価でのフォールバックを検討）。
  - lot_size を銘柄別にする拡張は将来の改善候補。
- .env パーサは多くの形式をサポートするが、極端なケースの互換性（シェルの全挙動再現）は保証しない。
- Monitoring は常に本番 sqlite_path を使用する設計（意図的）。Paper trading 監視を分離したい場合は run_monitoring 側の呼び出し先を変更する必要がある。
- コード内に DEBUG/INFO ログメッセージや TODO コメントあり。運用上の細かいチューニングは今後の改善事項。

References
- ソースファイル群を基に CHANGELOG を作成しました。実装の詳細や未完成点は該当ファイルのコメント/TODO を参照してください。