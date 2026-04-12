# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-12

### Added
- 基本アプリケーション初期リリース。
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"

- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - プロセス起動時にプロセス優先度を "high" に設定（psutil を利用）。
    - DB 接続は環境に応じて分離:
      - 本番/開発: settings.sqlite_path（デフォルト data/monitoring.db）。
      - Paper Trading (KABUSYS_ENV=paper_trading): settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して発注周りを完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てと ExecutionEngine の run_session 呼び出し。
    - duckdb 接続を併用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番 sqlite_path を利用する設計（監視データは本番 DB に記録）。
    - 例外耐性: check_once() の例外をログに記録して次ループへ継続。
    - KeyboardInterrupt ハンドリングによる正常終了処理（DB 接続クローズ等）。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートの判定は .git または pyproject.toml）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 解析は export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント (スペース直前の #) に対応。
    - Settings クラスを提供し各種設定をプロパティで取得:
      - J-Quants / kabu API / LINE / DB パス (duckdb/sqlite/paper_sqlite) / 監視設定 (pid/kill flag) /閾値 (CPU/MEM/DISK)/環境 (KABUSYS_ENV)/LOG_LEVEL 等。
    - バリデーション:
      - KABUSYS_ENV は development/paper_trading/live のいずれか。
      - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。
      - PAPER_FILL_MODE は instant/partial/never/reject のいずれか（不正値で ValueError）。

- ポートフォリオ構成モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋同点時 signal_rank でタイブレークして上位 N を選定。
    - calc_equal_weights: 等金額配分 (1/N)。
    - calc_score_weights: スコア比率で配分、全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバック（WARNING）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を算出。lot_size（単元）単位で丸め、per-position 上限・aggregate cap（available_cash）を考慮してスケーリングする実装。
    - コストバッファ(cost_buffer) を考慮した保守的見積りと、残差配分ロジックを実装。

- 監視・ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度設定を提供（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity を設定する set_cpu_affinity を提供（指定コア数の固定、エラー発生時は警告でスキップ）。
    - 権限不足や非対応 OS の場合に安全にスキップする挙動。

- 研究/ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算（true_range の NULL 伝播を厳密に制御）。
    - calc_value: raw_financials と prices_daily を組合せて PER / ROE を計算（target_date 以前の最新財務データを選択）。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算。horizons のバリデーションあり。
    - calc_ic: Spearman ランク相関（IC）計算。データ不足時は None を返す。
    - rank / factor_summary: ランク付け・基本統計量（count/mean/std/min/max/median）算出。
  - research/__init__.py エクスポート便利関数を用意（zscore_normalize は data.stats からインポート）。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini, JSON Mode) へバッチ送信して銘柄毎のセンチメント ai_score を作成・ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ（JST）を明確に定義し、calc_news_window ヘルパーを提供（前日15:00～当日08:30 JST に対応）。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの文字数・記事数上限を設定してトークン爆発を抑止（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - エラーハンドリング: 429/ネットワーク/5xx に対して指数バックオフでリトライ、失敗時はフェイルセーフで継続。
    - レスポンスバリデーションとスコアクリップ（±1.0）、部分成功時に既存スコア保護のため該当コードのみ置換する戦略（DELETE+INSERT の局所更新）。
    - API キーは引数または環境変数 OPENAI_API_KEY で供給（未設定時は ValueError）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト（CLI）。
    - DB パスはオプション --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db の順で解決。
    - 指標:
      - 稼働率 (uptime_pct)、注文成功率 (fill_rate_pct)、送信率 (send_rate_pct)、P95 レイテンシ (p95_ms)、リスク却下数。
    - 基準値（PASS/FAIL）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ (--from / --to) を受け取り ISO8601 UTC 範囲でクエリ実行。
    - 報告は標準出力へ整形出力。

### Security
- .env 自動読み込み時、OS 環境変数は protected として .env.local による上書きを防止する保護ロジックを実装。

### Notes
- DuckDB / SQLite を両方使用する構成になっており、分析系は DuckDB、監視・一部発注ログは SQLite を想定。
- 各モジュールは「副作用のない純粋関数」設計（特に portfolio モジュールや research モジュール）を意識しており、単体テストが容易な構成。
- 一部コメント・TODO に将来的拡張案（銘柄ごとの lot_size マスタ、価格フォールバック等）が記載されています。

### Breaking Changes
- 初回リリースのため該当なし。

---