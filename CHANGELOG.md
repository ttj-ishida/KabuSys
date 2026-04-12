# Changelog

すべての変更は Keep a Changelog の形式に従い、重大度順に記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-12

Initial release — 基本機能の第一実装を行いました。主な追加点・設計方針は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - Settings クラスによる環境変数 / .env ファイル読み込み・管理機能を実装。
    - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を探索して行う。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサーは export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントなどに対応。
    - 各種設定プロパティ（DBパス、PID ファイル、監視閾値、PAPER_FILL_MODE 等）を提供。
    - env 値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装し、不正値は ValueError を送出する。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite DB を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory 経由で MockBrokerClient / 実ブローカーを切り替え可能。
    - 各種実行コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッション実行。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
    - 起動時にプロセス優先度を "high" に設定し、DuckDB/SQLite 接続のクローズを保証。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を使用して監視データを集中管理。
    - 起動時にプロセス優先度を "high" に設定、監視ループは KeyboardInterrupt を処理して安全に終了。

- 監視関連
  - monitoring_db 初期化を起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を実装（psutil ベース）。
    - Windows の優先度クラス、POSIX の nice 値マッピング（high/normal/low）を提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を提供（引数 None で変更しない）。
    - サポート外 OS や権限不足時は警告を出してスキップするフェイルセーフ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・同点タイブレークでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を満たすための候補除外ロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投入資金乗数を返す（未知レジームは警告後 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算。以下をサポート:
      - risk_based: 許容リスク率・損切り率に基づく株数計算。
      - equal/score: 比率に基づく配分、max_position_pct、max_utilization、lot_size、cost_buffer を考慮した集約キャップとスケールダウン処理。
      - lot_size（単元）に基づく丸め、残余キャッシュで端数を lot 単位で再配分するロジック。
      - 価格欠損時には該当銘柄をスキップし、デバッグログ出力。

- リサーチ / ファクター計算（DuckDB 使用）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（ウィンドウ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR（ATR/close）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から直近財務を取得して PER / ROE を計算。
    - 全関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、外部 API に依存しない設計。

  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンをまとめて取得。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）では None を返す。
    - rank / factor_summary: ランク化（同順位は平均ランク）・ファクターの統計サマリ（count, mean, std, min, max, median）を提供。
    - 標準ライブラリのみで実装、pandas 等に依存しない。

- AI ニュース NLP スコアリング
  - ai.news_nlp
    - raw_news / news_symbols から記事を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
    - 実装の主な特徴:
      - ニュース収集ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（内部的に UTC に変換）。
      - 1 チャンク最大 20 銘柄（_BATCH_SIZE）。
      - 1 銘柄あたり最大記事数 / 最大文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフで最大 _MAX_RETRIES 回リトライ。
      - OpenAI のレスポンスは JSON Mode を想定し、厳密な JSON 構造（{"results": [{"code": "...", "score": ...}, ...] }）を検証。
      - 取得スコアは ±1.0 にクリップして正規化。
      - 成功した銘柄のみ ai_scores テーブルへ置換的に書き込み（部分失敗時に他銘柄の既存スコアを保護）。
      - API キーは引数 api_key または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を実装（python -m kabusys.tools.paper_verification_report）。
    - オプション: --from / --to（YYYY-MM-DD）、--db（DB パス）。
    - デフォルト DB は data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
    - 指標:
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
      - 標準の合格基準（稼働率 >= 99.0%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - DB テーブルが存在しない場合は安全に N/A を扱う。

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Security
- （特記事項なし）  
  - 注意: OpenAI API キー等の秘密情報は環境変数経由で管理する設計を取っています。コード内に平文トークンを置かないでください。

### Notes / 実装上の注意点
- DuckDB / SQLite を同時に利用する設計になっています（分析は DuckDB、軽量ログは SQLite）。
- run_monitoring は監視用 DB（sqlite_path）を「環境にかかわらず」使用するため、paper_trading モードでも監視は本番 DB に書き込む設計意図がある点に注意してください（コメントに明示）。
- process_priority の設定は権限やプラットフォームに依存するため、失敗時は警告ログを出して処理を継続します。
- 一部関数はデータ不足時に None を返すことを仕様としており、呼び出し側での扱いに注意してください（例: ファクターの ma200_dev, atr_20 など）。
- position_sizing の aggregate cap スケールダウンは lot_size 単位で丸めるため、端数処理によって期待した投下金額と差異が生じる場合があります。

---

今後の予定（非包括的）:
- 銘柄ごとの lot_size をマスター化して個別単元対応
- position_sizing の価格フォールバック（前日終値等）
- ai.news_nlp のエラー耐性強化と部分再実行機能
- テストカバレッジの追加（ユニットテスト / 統合テスト）

もし本 CHANGELOG に誤りや補足要望があれば教えてください。必要に応じて修正・追記します。