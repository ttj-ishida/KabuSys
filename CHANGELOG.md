# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
リリース日: 2026-04-09

## [0.1.0] - 2026-04-09

初回公開リリース。以下の主要機能を含みます。

### 追加
- 全般
  - パッケージ初期バージョンを設定（__version__ = "0.1.0"）。
  - 公開 API として主要モジュールを __all__ でエクスポート（data, strategy, execution, monitoring 等の意図的なトップレベル整理）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサー実装:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理。
    - インラインコメント処理（クォート有り/無しでの扱いを区別）。
  - 環境変数必須取得ユーティリティ `_require` と各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL など）。
  - 各種設定検証:
    - `PAPER_FILL_MODE` の許容値チェック（instant/partial/never/reject）。
    - `KABUSYS_ENV` の許容値チェック（development/paper_trading/live）。
    - `LOG_LEVEL` の許容値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - ファイルパス系設定は Path オブジェクトで返却（expanduser 対応）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算（各銘柄 1/N）。
    - calc_score_weights: スコア比率で正規化した重みを返却。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター別時価総額を計算し、1セクターの上限比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告ログとともに 1.0 でフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて注文株数を算出。
      - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）により株数を算出。
      - equal/score: weight に基づく投資額割当を算出。
      - per-stock 上限（max_position_pct）や単元（lot_size）で丸め、既存保有を考慮して追加発注数を算出。
      - aggregate cap: 全銘柄合計が available_cash を超える場合はスケーリングし、端数は lot_size 単位で残差が大きい順に再配分。
      - cost_buffer を考慮して手数料／スリッページを保守的に見積もる。

- リサーチ／ファクター計算（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB の prices_daily を用いて算出。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を算出。true_range 計算で NULL 伝播を慎重に扱う。
    - calc_value: raw_financials（最新 report_date <= target_date）と prices_daily を組み合わせて PER と ROE を算出（EPS が 0/NULL の場合は None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括クエリで取得。
    - calc_ic: factor と将来リターンを code で結合し、Spearman ランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank / factor_summary: 同順位は平均ランクとするランク付け、及び基本統計量（count/mean/std/min/max/median）を計算。
  - 実装方針として DuckDB 接続を受け取り外部 API に依存しない設計。

- AI（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを付与し ai_scores に書き込む機能を実装。
    - ニュース収集ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたりの文字数・記事数上限（_MAX_CHARS_PER_STOCK, _MAX_ARTICLES_PER_STOCK）。
    - API 呼び出しはリトライ（429/タイムアウト/ネットワーク/5xx）、レスポンスの厳格なバリデーション、スコアの ±1.0 クリップ。
    - DuckDB への書き込みはトランザクションで冪等（DELETE → INSERT）。部分失敗時に他銘柄の既存スコアを保護する設計。
  - regime_detector
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュース LLM センチメントを合成して日次の market_regime（bull/neutral/bear）を判定する機能を実装。
    - マクロニュース抽出はキーワードベースのフィルタ（設定されたキーワードリスト）でタイトルを取得。
    - 合成は重みづけ（MA 70%、マクロ 30%）、スケール・閾値でラベル付け。LLM 失敗時は macro_sentiment=0.0 でフォールバック。
    - 判定結果を market_regime テーブルへ冪等書き込み。

- 監視ログ（kabusys.monitoring）
  - monitoring_db
    - SQLite ベースの監視ログ永続化レイヤを提供。system_status, trade_logs, positions, risk_logs 等のテーブル作成用 init 関数を実装（冪等）。
    - 必要なインデックスも自動作成。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の注意点 / TODO
- position_sizing:
  - 現在 lot_size は全銘柄共通の引数として扱う。将来的に銘柄毎の単元情報（stocks マスタ）を与えて拡張する予定（コード中に TODO コメントあり）。
- apply_sector_cap:
  - price_map に価格欠損（0.0）がある場合、エクスポージャーが過少見積りされ意図しないブロック解除が起きうる。将来的に前日終値や取得原価を用いるフォールバックを検討。
- AI モジュール:
  - OpenAI 呼び出しは外部 API に依存するため、テストでは _call_openai_api をモックすることを想定。
  - レスポンスのフォールバックやリトライ戦略は実運用での監視が必要。
- データベース互換性:
  - DuckDB の executemany の仕様（空リスト不可など）に合わせた実装になっているため、DuckDB バージョンや将来的な互換性に注意。

### セキュリティ
- 初期リリースではセキュリティ関連の既知の脆弱性は特に報告なし。ただし、OpenAI API キーや J-Quants トークンなどの機密情報は環境変数で管理すること（.env はローカルのみ、リポジトリに含めないこと）を強く推奨。

---

将来的なリリースでは、単元株ごとの lot_size 対応、価格フォールバックロジック、より細かなエラーハンドリング改善、テストカバレッジ拡充などを予定しています。