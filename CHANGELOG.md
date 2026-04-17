# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

※この履歴はコードベースの内容から推測して作成しています（自動生成・実装からの推測に基づく説明）。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリースを公開。モジュール群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AIニューススコアリング、ユーティリティ、ツール）を収録。
  - パッケージメタ情報（kabusys.__version__ = "0.1.0"）を追加。

- 実行 / 運用
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。
    - stop フラグ検出（data/stop_requested.flag）で安全に停止。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。

- 設定 / 環境変数ロード
  - config.Settings クラスを追加。
    - 各種環境変数（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境モード等）をプロパティとして提供。バリデーション（有効値チェック）を実施。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の検証・デフォルトを実装。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH をサポート。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 読み込み時に OS 環境変数を保護する機能を導入（protected set）。

- .env パーサー
  - export KEY=val、クォート付き値（シングル/ダブル）のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応する堅牢な行パーサーを実装。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しにより監視テーブルを冪等に初期化する仕組みを追加（monitoring 側で使用）。

- ポートフォリオ構築
  - portfolio.portfolio_builder
    - select_candidates: スコア降順（スコア同点は signal_rank 昇順）で候補選定。
    - calc_equal_weights / calc_score_weights: 等比率・スコア加重配分の実装（全スコアが 0 の場合は等金額配分にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有時価ベースで判定）。"unknown" セクターは制限対象外とする挙動。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap スケールダウン、cost_buffer（手数料・スリッページ見積）を実装。
    - aggregate スケーリング時に fractional remainder に基づく追加配分ロジックを実装し、再現性確保のため安定ソートを採用。

- リサーチ（DuckDB ベース）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200乖離を計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials（最新）と株価から PER / ROE を計算。
    - DuckDB を利用した高性能な SQL ベース実装。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons 検証（正の整数かつ <=252）を実装。
    - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 件未満なら None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量サマリー（count/mean/std/min/max/median）を実装。
    - 浮動小数による ties 問題を低減するため rank 前に round(..., 12) を使用。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI API（デフォルト model: gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（1 API コールで最大 _BATCH_SIZE 件）とトークン肥大化対策（1銘柄あたり最大記事数／最大文字数でトリム）を実装。
    - 429・ネットワーク・タイムアウト・5xx に対する指数バックオフのリトライ、API キー解決（引数または OPENAI_API_KEY 環境変数）を実装。
    - レスポンスのスキーマ検証、スコアの ±1.0 クリップ、部分更新による既存スコア保護（対象コードに絞った DELETE/INSERT）等を考慮。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成 CLI を追加。
    - 稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を算出し、PASS/FAIL 判定を出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義、日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を提供。
    - set_cpu_affinity: 指定コア数での CPU affinity 固定を提供。権限制約時は警告を出してスキップ。

### Changed
- デフォルト動作
  - 監視ループは MONITOR_POLL_INTERVAL 環境変数で柔軟に調整可能になり、0 以下や不正値は安全にデフォルト（60 秒）へフォールバックするように改善。

### Fixed
- .env パーサーの改善により次の問題を解消・軽減:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの誤解釈などを正しく処理するように修正。
- position_sizing の aggregate cap スケールダウンでの非効率な割当を改善:
  - lot_size 単位の端数管理と残余キャッシュによる追加配分を実装し、より効率的かつ再現性のある配分を実現。
- research.calc_forward_returns の入力検証を追加:
  - horizons が不正な値（負数・0・252 超など）の場合に ValueError を発生させ、誤用を防止。

### Security
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用。未設定時は明示的なエラーを出して処理を中断し、誤った公開を防止。

### Notes / Implementation details
- DuckDB を分析処理（prices_daily / raw_financials 等）に使用。Execution/Monitoring の永続化は SQLite を使用（paper_trading モードは専用 DB で隔離）。
- 多くの機能は「DB 参照なし — 純粋関数（メモリ内計算）」の設計指針に従っており、単体テストが容易になるよう配慮されている（portfolio や position sizing 等）。
- いくつかの TODO がコード中に残っており（例: price のフォールバック、銘柄別 lot_size の導入など）、将来的な拡張が想定される。

---

今後のリリースでは、以下の改善が想定されます（コードや TODO コメントからの推測）:
- 銘柄別の単元株（lot_size）対応、手数料・スリッページモデルの精緻化。
- price 欠損時のフォールバック（前日終値や取得原価の採用）。
- AI モジュールのエラー時ロギング・部分リトライの強化および課金最適化。
- 追加の監視アラート（LINE 通知等）、ExecutionEngine の詳細なシャットダウンハンドリング強化。

---