# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティック バージョニングを採用しています。

なお、以下の記載はコードベースから推測してまとめた要約です（実装コメント・ロジックに基づく記述）。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-13
初回リリース。主要なモジュール群および起動スクリプト、ツール、研究用ユーティリティを追加。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは `__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite DB（デフォルト `data/paper_trading.db`）を使用し、MockBrokerClient による完全分離された紙上トレードを可能にする。
    - プロセス優先度を起動時に "high" に設定（set_process_priority）。
    - 必須依存のコンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッション実行。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）を提供し、初期ポートフォリオ値は broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値（0以下や非整数）はログ警告のうえデフォルトにフォールバックする。
    - 監視処理は環境にかかわらず本番用の `sqlite_path` を使用して monitoring DB を初期化する設計。
    - プロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - 環境変数と .env ファイルの読み込みロジックを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を行い、見つかった場合に `.env` と `.env.local` を読み込む（優先順位: OS 環境変数 > .env.local > .env）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パーサーは export プレフィックス、クォート・エスケープ、行内コメントルール等に対応。
    - Settings クラスを通じて各種設定プロパティを提供（DB パス、PID/kill flag、閾値、環境種別判定、paper_trading 関連設定など）。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を実装。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）を実装。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows / POSIX に対応）。
    - set_process_priority(level) — "high" / "normal" / "low" をサポート。アクセス権限や未対応プラットフォーム時はログ警告でスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数に CPU affinity を設定（None で何もしない）。不正な cpu_count に対する検証あり。失敗時は警告でスキップ。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択（signal_rank による tiebreak）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア正規化による重み付け（全スコアが 0 の場合は等配分へフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有に基づくセクター集中度チェック機能。売却予定銘柄は除外可能。unknown セクターは上限適用外。
    - calc_regime_multiplier: マーケットレジーム（"bull","neutral","bear"）に応じた投資乗数を返す（未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・現金・現物保有・価格等を元に単元株丸めを含む発注株数計算を実装。risk_based / equal / score の allocation_method をサポート。
    - aggregate cap（全銘柄合計が available_cash を超える場合のスケーリング）や lot_size（単元）・cost_buffer を考慮した保守的算出を実装。

  - portfolio/__init__.py にて主要関数群をエクスポート。

- 研究・ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB の prices_daily 参照で計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を結合して PER/ROE を算出（target_date 以前の最新財務を使用）。

  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターン間の Spearman ランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank: 値を平均ランクに変換（同順位は平均順位）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。

  - research/__init__.py で上記をエクスポート（zscore_normalize は kabusys.data.stats からインポート）。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を実装。
    - target_date に対するニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST、UTC に変換）を用いて対象記事を収集。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、最大記事数／文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーション、スコアを ±1.0 にクリップし、ai_scores テーブルへの安全な部分置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）を行う。
    - OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が未設定の場合は ValueError。
    - 実装上、API 失敗時はスキップして処理継続するフェイルセーフ設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加（モジュールとして実行可能: python -m kabusys.tools.paper_verification_report）。
    - デフォルト DB: `data/paper_trading.db`、オプションで --db を指定可能。期間フィルタ --from / --to（YYYY-MM-DD）。
    - システム稼働率（system_status）、注文成功率/送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（P95 等）を集計してテキストレポートを出力。
    - 判定基準（デフォルト閾値）:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - レポートはデータ不足時に N/A を表示し、FAIL 条件の詳細を列挙。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- 環境変数の自動ロードはプロジェクトルートが検出できない場合はスキップされるため、配布環境やインストール後の挙動に影響しない設計。
- .env 読み込みは OS 環境変数を保護するため protected セットを使って上書きを制御する（.env.local は override=True だが OS 変数は上書きされない）。
- DuckDB をデータ分析用途に使用（research / ai など）し、prices_daily / raw_financials / raw_news / news_symbols / ai_scores テーブルを参照する前提。
- run_monitoring と run_execution はどちらもプロセス優先度を高くセットしようとするため、実行環境の権限によっては警告が出力される可能性がある。

### Breaking Changes
- なし（初回リリース）

---

参考: 各スクリプトはモジュールを直接実行できるように `if __name__ == "__main__": main()` を持ちます。環境変数や DB パスの設定に注意して下さい。