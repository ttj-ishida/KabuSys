# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な変更はセマンティックバージョニングに基づいて記載しています。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（今後の変更や修正をここに記載します）

---

## [0.1.0] - 初回リリース
初期実装リリース。自動売買 / リサーチ / AI 補助のコア機能を含む。

### 追加 (Added)
- 全体
  - パッケージメタ情報を実装（kabusys.__version__ = 0.1.0）。
- 環境・設定管理 (src/kabusys/config.py)
  - .env/.env.local および環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して検出。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の柔軟なパース（export 形式、シングル・ダブルクォート、インラインコメント取り扱い、エスケープ処理等）を実装。
  - 必須設定取得ヘルパー (_require) を実装（未設定時は ValueError を送出）。
  - 各種設定プロパティを実装（J-Quants, kabu API, LINE, DB パス, Paper Trading 設定, 監視閾値, 環境・ログレベル検証等）。
    - デフォルト値: KABU_API_BASE_URL="http://localhost:18080/kabusapi", DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db", PAPER_TRADING_SQLITE_PATH="data/paper_trading.db" 等。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL に対する値検証（不正な値は ValueError）。
- ポートフォリオ構築 (src/kabusys/portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分ロジックを実装。全スコアが 0 の場合は等分配にフォールバックし警告を出力。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が指定上限を超える場合、新規候補をセクター単位で除外。
      - セクター不明 ("unknown") は上限適用対象外。
      - 当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告を出し 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: 複数の割当方式に対応した株数決定ロジックを実装。
      - allocation_method="risk_based"（許容リスク率に基づく）および "equal"/"score" に対応。
      - lot_size（単元）丸め、1銘柄上限・aggregate cap（利用可能現金）でスケーリング。
      - cost_buffer を使った手数料・スリッページ保守的見積り。
      - aggregate cap 超過時はスケーリングと端数（lot 単位）再配分ロジックにより再計算。
      - 将来的な拡張点として銘柄別 lot_size の導入を想定（TODO コメントあり）。
- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB の prices_daily を使って算出。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に処理。
    - calc_value: raw_financials から最新財務（target_date 以前）を取得し PER・ROE を算出。EPS が 0 や欠損の場合は PER を None。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の検証（正の整数かつ <=252）。
    - calc_ic / rank: スピアマンランク相関（IC）算出ロジックと同順位の平均ランク処理を実装。IC は有効レコード 3 件未満で None を返す。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
  - research パッケージの __all__ を整備し zscore_normalize（kabusys.data.stats から）等をエクスポート。
- AI（LLM）関連 (src/kabusys/ai)
  - news_nlp:
    - calc_news_window: news 収集ウィンドウ（JST ベース -> UTC 変換）を算出するユーティリティを実装。
    - score_news: raw_news と news_symbols を集約し、OpenAI API（gpt-4o-mini）を用いて銘柄ごとにセンチメント（ai_score）を算出、ai_scores テーブルへ安全に書き込む処理を実装。
      - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたり記事トリム制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - OpenAI 呼び出しは JSON Mode を利用し、429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ。その他エラーはフェイルセーフでスキップ。
      - レスポンスの厳密なバリデーションを行い、未知コードや非数値スコアは無視。スコアは ±1.0 にクリップして保存。
      - DuckDB への書き込みは部分失敗時に既存データを守るため、対象コードのみ DELETE → INSERT を実行（トランザクション制御）。
    - テスト容易性のために API 呼び出し部分は _call_openai_api を経由して差し替え可能。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 0.7）とマクロニュース LLM センチメント（重み 0.3）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み。
      - 1321 の MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は中立（ma200_ratio=1.0）にフォールバックして警告。
      - マクロニュースはキーワードフィルタ（複数キーワード）で抽出し、LLM 呼び出し失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
      - OpenAI 呼び出し部分もテスト差し替え可能な実装。
- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite を使った監視用 DB の初期化（複数テーブルとインデックス作成）を実装（冪等）。
    - system_status, trade_logs, positions, risk_logs などのテーブルを作成するスクリプトを含む（ファイル途中までの実装確認済み）。

### 変更 (Changed)
- N/A（初回リリースのため既存からの変更なし）

### 修正 (Fixed)
- N/A（初回リリース）

### 非推奨 (Deprecated)
- N/A

### 削除 (Removed)
- N/A

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して明示的に失敗する実装となっているため、取り扱いに注意。
- .env 自動ロードはデフォルトで有効だが、テストなどで無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を提供。

---

補足 / 既知の制約と今後の改善予定
- apply_sector_cap: price_map に 0.0（欠損）が含まれる場合、エクスポージャーが過少見積もられブロックが外れる可能性あり。将来的に前日終値や取得原価などのフォールバック価格を導入予定（TODO）。
- position_sizing: 現状 lot_size は全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を予定（TODO）。
- news_nlp / regime_detector: LLM 呼び出しの失敗時はフォールバック値で継続する実装（フェイルセーフ）だが、API の利用回数や課金面の影響を考慮した運用設計が必要。
- research モジュールは DuckDB の特定テーブル（prices_daily / raw_financials 等）構造に依存するため、スキーマ変更時は対応が必要。

もし CHANGELOG に追記してほしい詳細（例えばより細かなコミット単位の変更点やリリース日など）があれば教えてください。必要に応じて英語版も作成できます。