# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
初回公開にあたり、コードベースから推測できる主要な機能追加・設計上の振る舞い・注意点をまとめています。

## [0.1.0] - 2026-04-12

### Added
- 基本パッケージ情報
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。
- 実行用エントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。無効値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB は環境に依存せず本番の sqlite_path を使用する（監視データは分離しない設計）。
    - 起動時にプロセス優先度を "high" に設定（ユーティリティ経由）。
    - SQLite / DuckDB 接続を確立し、ループ内で monitor.check_once() を定期実行。例外はログに記録して次回ポーリングへ継続。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite DB（`data/paper_trading.db` または環境変数で上書き）を使用し、本番 DB と完全分離する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory を用いたブローカークライアント作成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の run_session 呼び出し。
- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート検知: .git または pyproject.toml）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
    - .env パーサ実装:
      - export キーワード対応、シングル/ダブルクォート対応（バックスラッシュエスケープも処理）、インラインコメントの扱い（条件付きでコメント認識）。
      - override / protected オプションによる上書き制御（OS 環境変数保護）。
    - Settings クラスを提供:
      - 各種設定プロパティ（DB パス、PID/KILL フラグ、閾値、API トークンなど）。
      - 値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック等）。
      - paper_trading 用の paper_sqlite_path、paper_fill_mode の取り扱い。
- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db の呼び出しにより監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority(level) を追加。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加（利用不可や権限不足は警告でスキップ）。
    - 権限不足や未対応 OS に対して安全にフォールバックする設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルのスコア順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア合計ゼロは等配分にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear・未知値は 1.0 で警告フォールバック）。
    - 一部挙動に関する注意（価格欠損時の TODO コメントなど）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate cap (available_cash) に応じたスケーリングを実装。
    - cost_buffer による保守的コスト見積り、残差処理で lot 単位追加配分のロジックを実装。
- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率などを DuckDB の prices_daily テーブルから算出。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を算出（欠損ハンドリングあり）。
    - calc_value: raw_financials と prices_daily を組み合わせ PER/ROE を算出（最新財務レコードの選択ロジック含む）。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic: スピアマン順位相関（IC）を計算。サンプル数が不足する場合は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量サマリを提供。外部ライブラリに依存しない純粋実装。
  - research.__init__ にて zscore_normalize（kabusys.data.stats）との統合エクスポート。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとの ai_scores を更新する処理を実装。
    - 処理フロー:
      - スコア算出対象ウィンドウ（JST 基準で前日 15:00 ～ 当日 08:30）を計算（UTC 変換）。
      - 記事を銘柄ごとに集約（最大記事数・文字数でトリム）。
      - 最大 _BATCH_SIZE (=20) 銘柄ずつバッチ送信、JSON モードでレスポンスを期待。
      - 429/ネットワーク/5xx に対して指数バックオフでリトライ（_MAX_RETRIES）。
      - レスポンスのバリデーションとスコアの ±1.0 クリッピング。
      - 成功した銘柄のみを ai_scores テーブルで差し替え（DELETE→INSERT、部分失敗時に既存スコアを保護）。
    - OPENAI_API_KEY の未設定時は ValueError を送出。
    - executemany の制約や API の失敗時はフェイルセーフでスキップする設計。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 指標:
      - 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
      - 閾値はソース内定義（稼働率 >= 99%、fill_rate >= 90% 等）。
    - 出力は要約レポート（PASS/FAIL 判定）を標準出力へ表示。
    - P95 計算、期間フィルタ、DB 存在チェック、SQL の OperationalError に対する保護を実装。
- パッケージの公開 API エクスポート
  - portfolio / research / utils 等の主要関数を __all__ でエクスポートして簡単に利用可能に。

### Changed
- 起動順序に関する明示的な設計
  - run_monitoring/run_execution の起動時に最初にプロセス優先度を設定するように統一。
- DB の使い分け方針を明示
  - 監視用プロセスは本番 sqlite_path を使用（環境に依らない）。実行エンジンは paper_trading 環境時に専用 DB を使用して本番と分離する方針を採用。

### Fixed
- 環境パーサの堅牢性向上
  - .env のクォート／エスケープ／コメント処理の実装で実運用で問題になりやすいケースに対応。
- 計算モジュールの欠損データハンドリング
  - ファクター計算・ATR 等で行不足時に None を返す実装により N/A を明示して処理の安全化を図った。

### Notes / Known limitations
- apply_sector_cap の価格欠損時の扱いに TODO が残る（前日終値や取得原価でのフォールバックが未実装）。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出してスキップするため、優先度設定が保証されない場合がある。
- DuckDB / executemany に関するバージョン依存の挙動（空パラメータの扱い）に注意（コード中でチェックを行っている）。
- OpenAI API 呼び出しは外部サービスに依存するため、API キー管理・レート制限・コストに留意すること。
- run_monitoring が監視 DB として本番 DB を用いる点は設計上の判断であり、必要に応じて分離を検討すべき。

---

今後のリリースでは、テストカバレッジ、エラーハンドリングの強化、価格フォールバックの実装、銘柄別 lot_size 管理などの改善が想定されます。必要であれば、この CHANGELOG をベースに Unreleased セクションを追加して逐次更新できます。