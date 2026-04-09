CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- 特になし

[0.1.0] - 2026-04-09
-------------------

Added
- 基本パッケージ情報
  - パッケージ version を src/kabusys/__init__.py にて "0.1.0" として定義。
  - __all__ に主要サブパッケージを登録（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動的に .env/.env.local を読み込む。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パースは export 形式、クォート、エスケープ、コメント処理等に対応。
    - ファイル読み込み失敗時は警告を出し安全にスキップ。
  - Settings プロパティ（主なもの）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD の必須取得（未設定時は ValueError）。
    - KABU_API_BASE_URL, LINE_*、DBパス（DUCKDB_PATH, SQLITE_PATH）等の既定値。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許可）。
    - PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、閾値（CPU/MEM/DISK）等の型変換。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証。
    - 環境判定ヘルパー: is_live / is_paper / is_dev。

- ポートフォリオ構築コンポーネント (src/kabusys/portfolio/)
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソート（score 同値時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比例配分。全スコアが 0 の場合は等配分にフォールバックし WARNING をログ出力。
  - risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター比率が上限（デフォルト 30%）を超える際、新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告ログ）。
  - position_sizing.py:
    - calc_position_sizes: 株数決定ロジックを実装。
      - allocation_method に "risk_based" / "equal" / "score" をサポート。
      - risk_based: risk_pct, stop_loss_pct を使ったリスクベース算出。
      - equal/score: weight に基づく割当（max_position_pct, max_utilization を考慮）。
      - lot_size（単元）で丸め、単元単位でスケールダウンや再配分（残差を考慮して lot 単位で追加配分）。
      - aggregate cap: 合計投資額が available_cash を超えた場合のスケーリング（cost_buffer を考慮）。
      - 価格欠損時はスキップし、ログ出力で通知。

  - パッケージエクスポート（src/kabusys/portfolio/__init__.py）:
    - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier を公開。

- リサーチ / ファクター群 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離（ma200_dev）を DuckDB の prices_daily テーブルから計算。ウィンドウ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials の最新財務（report_date <= target_date）と当日株価を組み合わせて PER / ROE を算出。EPS 欠損または 0 の場合は PER を None に。
    - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照する設計（副作用なし）。
  - feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一クエリで取得。horizons の検証あり（1..252）。
    - calc_ic: Spearman ランク相関（IC）を計算。データ不足（有効レコード <3）や分散ゼロ時は None を返す。
    - rank: 同順位は平均ランクを返す（丸め誤差対策に round で正規化）。
    - factor_summary: count/mean/std/min/max/median を計算。None を除外。
  - パッケージエクスポート（src/kabusys/research/__init__.py）:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank。

- AI 統合（OpenAI）モジュール (src/kabusys/ai/)
  - news_nlp.py:
    - score_news(conn, target_date, api_key=None):
      - raw_news + news_symbols を集約して各銘柄のニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む。
      - ニュースウィンドウは target_date を基準に JST で前日15:00〜当日08:30（内部は UTC に変換）を計算。calc_news_window 関数を公開。
      - 1銘柄当たり最大 _MAX_ARTICLES_PER_STOCK（既定10）記事、最大文字数トリム（既定3000文字）。
      - バッチ処理: 最大 _BATCH_SIZE（既定20）銘柄で API コール。
      - API 呼び出しは JSON Mode とし、429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ（デフォルト 3 回）。
      - レスポンス検証: JSON パース、"results" 配列、code の整合性、スコア数値性を確認。スコアは ±1.0 にクリップ。
      - DB 書き込みは冪等化（BEGIN → DELETE（該当 code）→ INSERT → COMMIT）し、部分失敗時に他コードを消さない設計。
      - api_key が未指定かつ OPENAI_API_KEY が未設定の場合は ValueError を送出。
      - テストしやすさ: _call_openai_api は差し替え可能（テスト用 patch を想定）。
    - 内部に _fetch_articles, _score_chunk, _validate_and_extract 等の補助関数を実装。
  - regime_detector.py:
    - score_regime(conn, target_date, api_key=None):
      - ETF 1321（日経225連動型）の直近 200 日 MA 乖離（ma200_ratio）を算出（target_date 未満のデータのみ使用しルックアヘッドを防止）。
      - raw_news からマクロキーワード（日本/米国等）に該当するタイトルを抽出し、LLM でマクロセンチメントを評価（記事がない場合は 0.0 にフォールバック）。
      - 合成式: 0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment を clip(-1,1) して regime_score を作成。
      - threshold により regime_label を判定（bull/neutral/bear）。
      - DB への書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。
      - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - news_nlp の calc_news_window を再利用しつつ、OpenAI 呼び出しは独自実装でモジュール間の結合を避ける設計。
  - パッケージエクスポート（src/kabusys/ai/__init__.py）:
    - score_news を公開（regime_detector は直接公開していないがモジュールとして利用可能）。

- モニタリング永続化層 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db(conn): SQLite 接続に対して監視用テーブル（system_status, trade_logs, positions, risk_logs など）とインデックスを冪等的に作成するスクリプトを追加。
  - SQLite を使った単純読み書き層として設計（ビジネスロジックなし）。

Design / Quality / Safety
- ルックアヘッドバイアス対策:
  - AI モジュール・リサーチモジュールともに datetime.today() / date.today() を参照せず、明示的に target_date を受け取る設計。
  - prices_daily クエリでは必要に応じて date < target_date の排他条件を守る。
- テスト容易性:
  - OpenAI 呼び出しラッパー関数（_news_nlp._call_openai_api, regime_detector._call_openai_api）を patch で差し替え可能に設計。
  - DuckDB / SQLite 接続を外部から注入することでユニットテストが可能。
- フォールバック / 安全策:
  - API キー未指定時は明示的なエラー（ValueError）を返し、安全なデフォルト動作／フォールバック（macro_sentiment=0.0、未知レジーム=1.0、等）を多数導入。
  - 外部 API エラーに対するリトライと最終的フォールバック動作を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キー等の機密情報は環境変数経由で扱うことを想定。CHANGELOG に秘密情報は含めない。

Notes / TODO（コード内コメントとして記載）
- position_sizing: 将来的に銘柄別 lot_size 対応を想定（現状は共通 lot_size 引数）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格の採用を検討。
- news_nlp / regime_detector: LLM の挙動に依存する箇所があるため、応答検証と堅牢なフォールバックを重視。

-----