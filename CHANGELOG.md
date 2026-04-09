# Changelog

すべての注目すべき変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-09

初回公開リリース。本リリースでは、自動売買エンジンの設定管理、ポートフォリオ構築、リスク調整、ポジションサイジング、研究用ファクター計算、特徴量探索、AI を用いたニュースセンチメント評価、市場レジーム判定、監視ログ永続化の基本モジュールを実装しています。

### 追加 (Added)
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - 自動ロード優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD に依存しない）。
    - 環境変数自動ロードを停止するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの無視
    - クォートなし値のインラインコメント取り扱い（直前が空白/タブの場合のみ）
  - .env 読込みポリシー:
    - `.env` は既存 OS 環境変数を上書きしない（override=False）
    - `.env.local` は既存 OS 環境変数を保護しつつ上書き可能（override=True、ただし OS 環境変数キーは protected）
  - Settings クラスを提供（アプリ設定の一元取得）
    - API トークン / パスワード（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）や
      DB パス、Paper Trading 用設定、監視しきい値、環境種別（KABUSYS_ENV）、ログレベルなど。
    - バリデーション:
      - PAPER_FILL_MODE（instant/partial/never/reject）
      - KABUSYS_ENV（development/paper_trading/live）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - 必須設定は未設定時に ValueError を送出する `_require()` を使用。

- ポートフォリオ構築 (src/kabusys/portfolio/...)
  - 銘柄選定・重み計算（pure functions）
    - select_candidates: BUY シグナルをスコア降順、同率は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率による配分。全銘柄スコアが 0 の場合は警告を出して等金額配分にフォールバック。
  - リスク調整（セクター上限、レジーム乗数）
    - apply_sector_cap: 既存保有のセクター時価比率が上限を超えるセクターの新規候補を除外。`unknown` セクターは上限対象外。売却予定銘柄は露出計算から除外可能。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に対応する投下資金乗数（1.0/0.7/0.3）、未知レジームは警告後に 1.0 フォールバック。
  - ポジションサイジング（株数決定）
    - calc_position_sizes:
      - allocation_method: "risk_based"（リスク許容率と損切り率に基づく） / "equal" / "score"
      - 単元（lot_size）で丸め、1銘柄上限（max_position_pct）、全体の利用上限（max_utilization）を考慮。
      - aggregate cap: cost_buffer（手数料・スリッページ）を考慮して全銘柄コストが available_cash を超える場合にスケールダウンし、残差は lot 単位で分配する実装（端数配分は再現性を保つソートで決定）。
      - price 欠損（None/0）の場合はスキップ。将来的に価格フォールバックを追加する旨の TODO 記載。

- 研究用モジュール (src/kabusys/research/...)
  - ファクター計算 (factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（MA200 が充分な行数でない場合は None）。
    - calc_volatility: 20日 ATR（true range の NULL 伝播を制御）、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し PER（EPS により None あり）、ROE を計算。
    - すべて DuckDB（prices_daily / raw_financials）を参照し、外部 API にはアクセスしない設計。
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: LEAD を使って複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons は正の整数かつ 252 以下で検証。
    - calc_ic: スピアマンランク相関（ランクは同順位を平均ランクで処理、丸めを使って ties を安定化）。有効レコードが 3 未満なら None。
    - factor_summary: count/mean/std/min/max/median の集計（None を除外して計算）。
    - rank: ランク変換ユーティリティ（同順位平均ランク、round(...,12) による安定化）。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。

- AI 関連 (src/kabusys/ai/...)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - score_news: raw_news + news_symbols から銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を計算して ai_scores テーブルに書き込む。
    - バッチ処理: 最大 20 銘柄/リクエスト、記事・文字数の上限（記事最大 10 件 / 銘柄、最大 3000 文字）でトリム。
    - エラー処理: 429・ネットワークエラー・タイムアウト・5xx は指数バックオフでリトライ。それ以外は失敗したチャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON 抽出、"results" リストの確認、各要素に code/score があり、要求したコード集合に含まれるかを検証。スコアは ±1.0 にクリップ。
    - DB 書き込み: 部分失敗時に既存の他銘柄スコアを消さないため、対象コードごとに DELETE → INSERT を行う（トランザクション処理、ROLLBACK 保護）。
    - テスト容易性: `_call_openai_api` をモック可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime: ETF 1321 の MA200 乖離（直近 200 日）とマクロニュースの LLM センチメントを合成してレジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースはタイトルベースでキーワードフィルタ（多数の日本語・英語キーワード）を適用。API 失敗時は macro_sentiment=0.0 で継続。
    - LLM 呼び出しと retry 処理は news_nlp と独立した実装（モジュール結合を避ける）。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite 接続に対して冪等的にテーブル・インデックスを作成するユーティリティを追加。
    - 作成する主なテーブル: system_status, trade_logs, positions, risk_logs（ファイル内に記載の通り複数テーブルとインデックスを準備）。
    - 監視用途の永続層としてビジネスロジックを持たず読み書きのみを担当。

- パッケージエクスポート
  - kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier を再エクスポート。
  - kabusys.research: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank をエクスポート。
  - kabusys.ai: score_news をエクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制約・注意点 (Known issues / Notes)
- 環境変数の必須受け取り
  - J-Quants・kabu API などの必須値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと ValueError を送出するため、運用前に .env あるいは環境変数を適切に準備してください。
- .env ロード
  - 自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後の挙動等を配慮）。
- 価格欠損について
  - apply_sector_cap の露出計算で price_map が 0.0 の場合に露出が過少見積りされる可能性があり、将来の拡張で前日終値や取得原価へのフォールバックを検討中（コード内に TODO）。
- 単元株（lot_size）の将来的拡張
  - 現状は global な lot_size を想定。将来的には銘柄ごとの lot_size を受け取る拡張を予定（コード内に TODO）。
- DuckDB / SQLite の executemany の制約
  - DuckDB 0.10 の挙動に合わせ、executemany に空リストを渡さないガードを実装している（互換性向上のため）。
- LLM 依存機能は外部 API の可用性に依存する
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini）に依存する。API キー未設定時は明確なエラーまたはフォールバック（macro_sentiment=0.0）を行う設計。
- テスト設計
  - AI 呼び出し部分は `_call_openai_api` を patch/mock してテスト可能な構造にしている。

### 互換性（Breaking Changes）
- 初回リリースのため破壊的変更はありません。

---

今後の予定（抜粋）
- 銘柄別 lot_size を持つ拡張（stocks マスタ反映）
- apply_sector_cap の価格フォールバック実装（前日終値等）
- 追加ファクター・IC 分析の拡張・可視化ユーティリティ

もし特定機能の詳細（引数や返り値、エラー挙動など）を CHANGELOG に追記したい場合は、そのモジュール名を指定してください。