CHANGELOG
=========

このファイルは "Keep a Changelog" の様式に準拠しています。  
主な変更点はセマンティックバージョニングに従って記載しています。

Unreleased
----------
- 予定 / 既知の改善点（今後のリリースで対応予定）
  - position_sizing: 銘柄ごとの単元（lot_size）を stocks マスタで管理する拡張。
  - risk_adjustment.apply_sector_cap: 価格欠損（price == 0.0）のフォールバック（前日終値等）を導入し、エクスポージャーの過少見積り問題を解消。
  - research.calc_value: PBR・配当利回りなどのバリューファクターを追加。
  - ai.news_nlp / ai.regime_detector: OpenAI SDK の将来の変更に対する互換性テスト、及びレスポンスのより厳密な検証・ロギング強化。
  - テスト/CI: DuckDB executemany の空パラメータ制約や OpenAI 呼び出しのモックに関する統合テストの整備。
  - ドキュメント: API 使用例、および .env 自動ロードの挙動（KABUSYS_DISABLE_AUTO_ENV_LOAD など）に関する追加ドキュメント化。

[0.1.0] - 2026-04-09
-------------------
Added
- パッケージ基礎
  - 初期リリースを追加（バージョン: 0.1.0）。
  - src/kabusys/__init__.py に __version__ = "0.1.0" とトップレベルの __all__ を設定。

- 環境・設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定読込を実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサーは export KEY=val、クォート、エスケープ、インラインコメントなどを考慮。
    - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などをプロパティ経由で取得。
    - 必須変数未設定時に ValueError を送出する _require 実装。
    - PAPER_FILL_MODE、LOG_LEVEL、KABUSYS_ENV 等の入力検証（許容値チェック）を実装。

- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates(buy_signals, max_positions): スコア降順で候補を選択（同点タイブレークあり）。
    - calc_equal_weights(candidates): 等金額配分（1/N）。
    - calc_score_weights(candidates): スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバックし WARNING ログを出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap(...): セクター集中の上限チェック。既存保有のセクター別時価から上限超過セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier(regime): market regime（bull/neutral/bear）に応じた投下資金乗数。未知レジームは 1.0 でフォールバックし警告ログを出す。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes(...): 銘柄ごとの発注株数を計算する主要関数を実装。
      - 対応する allocation_method: "risk_based", "equal", "score"。
      - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）に基づく計算。
      - equal/score: weight に基づく配分、portfolio_value・max_utilization・max_position_pct による上限適用。
      - lot_size（単元株）による丸め処理、cost_buffer を考慮した保守的コスト見積り、aggregate cap を超える場合のスケーリング、端数（fractional）を用いた追加配分ロジックを実装。
      - 価格欠損時はスキップし、適宜デバッグログ出力。

  - src/kabusys/portfolio/__init__.py
    - portfolio モジュールの公開 API（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）をエクスポート。

- リサーチ（ファクター計算・特徴量解析）
  - src/kabusys/research/factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、MA200 乖離を DuckDB 上の prices_daily を用いて計算。データ不足時は None を返す設計。
    - calc_volatility(conn, target_date): ATR20、相対ATR、20日平均売買代金、出来高比を計算。true_range の NULL 伝播を明示的に制御。
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER/ROE を計算（EPS が 0/NULL の場合は None）。
    - 各関数は DuckDB クエリで効率的に取得し、(date, code) キーの dict リストを返す。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズンの将来リターンを一括クエリで計算。horizons の検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。有効レコードが 3 未満なら None。
    - rank(values): 同順位は平均ランクにするランク関数（丸めで ties 回避）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算（None を除外）。
    - pandas 等外部依存無く標準ライブラリ + duckdb で実装する設計方針を採用。

  - src/kabusys/research/__init__.py
    - zscore_normalize（外部提供）と研究系 API をエクスポート。

- AI / NLP 機能
  - src/kabusys/ai/news_nlp.py
    - calc_news_window(target_date): JST ベースのニュースウィンドウ（前日15:00 JST〜当日08:30 JST）の UTC naive datetime を返すユーティリティ。
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) に渡し、銘柄ごとの ai_score を ai_scores テーブルに書き込むフローを実装。
      - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたりのトリミング制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - OpenAI 呼び出しは JSON Mode を利用。429 / ネットワークエラー / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他の例外は再試行しない。
      - レスポンスバリデーション: JSON パース、"results" 配列、各要素の code/score 検証、score を ±1.0 にクリップ。
      - 書き込みは冪等（DELETE → INSERT）で部分失敗時に既存スコアを保護する実装。DuckDB executemany の空リスト制約に配慮。
      - OpenAI API キーが未設定の場合は ValueError を送出。
      - フェイルセーフ: API 全失敗時は該当チャンクをスキップして処理継続。

  - src/kabusys/ai/regime_detector.py
    - score_regime(conn, target_date, api_key=None): ETF 1321 の MA200 乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成して当日の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする実装。
      - _calc_ma200_ratio: データ不足時は 1.0（中立）でフォールバックし警告ログを出力。
      - _fetch_macro_news: マクロキーワードで raw_news をフィルタ。
      - _score_macro: タイトル群が空なら LLM 呼び出しを行わず macro_sentiment=0.0 とする。API エラー時も 0.0 にフォールバック（警告ログ）。
      - 合成スコアをクリップし閾値に基づきラベル付け。DB 書き込みはトランザクションで行う。OpenAI キー未設定時は ValueError を送出。

  - src/kabusys/ai/__init__.py
    - score_news を公開 API としてエクスポート。

- 監視・ロギング永続化
  - src/kabusys/monitoring/monitoring_db.py
    - init_monitoring_db(conn): SQLite を用いた監視ログ永続化テーブル群（system_status, trade_logs, positions, risk_logs ...）とインデックス作成を実装（冪等）。（ファイル内でさらにテーブル定義が続く形で実装）

Security / Fixed
- 環境変数・秘密鍵の扱い
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用。未設定時は明確にエラー（ValueError）となるため、キー漏洩リスク低減の観点で environment-first の取り扱いを明示。

Notes / 動作上の注意
- DuckDB / SQLite への互換性
  - DuckDB の executemany に関するバージョン差異に注意（空リストバインド不可のため空チェックを挟んでいる）。
- ルックアヘッドバイアス対策
  - 日次の集計処理（news/regime/research）では datetime.today()/date.today() を直接参照せず、target_date ベースで処理する設計。
  - prices_daily クエリ等は target_date 未満の排他条件を意識している箇所がある。
- 既知の制約
  - 一部 TODO をコード内に記載（position_sizing lot_size の銘柄別対応、sector_exposure における price フォールバック等）。
  - news_nlp と regime_detector は OpenAI の JSON Mode を前提としているため、モデル/SDK 変化時に適合が必要。

----

貢献・バグ報告
- バグ報告や機能要望は Issue を立ててください。可能であれば再現手順と最小限のコード/データを添えてください。