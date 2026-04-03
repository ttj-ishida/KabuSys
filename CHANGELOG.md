# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

現在のリリース履歴:

## [0.1.0] - 2026-04-03

### 追加
- 初期リリース。KabuSys 日本株自動売買システムのコアライブラリを追加。
  - パッケージ公開情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - __all__ に data, strategy, execution, monitoring を公開（モジュール構成のエントリポイント）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）または OS 環境変数からの自動読み込みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点）。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応、行内コメント扱いのルール）。
  - Settings クラスを提供し、各種設定プロパティを環境変数から取得:
    - J-Quants / kabuステーション / LINE API / DB パス（DuckDB / SQLite）/ 監視用ファイルパス（PID / kill flag）/リソース閾値（CPU/メモリ/ディスク）/環境（development, paper_trading, live）/ログレベルなど。
  - 必須環境変数未設定時は ValueError を送出する _require() を実装。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols をもとに銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - バッチ処理、チャンク化（最大 20 銘柄／回）、1銘柄あたり記事数上限・文字数上限のトリム機能。
    - OpenAI 呼び出しのリトライ（429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ）、非リトライエラーはスキップ。
    - レスポンスの厳密バリデーション（JSON 抽出、results リスト、code と score の型チェック、スコアの ±1.0 クリップ）。
    - 書き込みは部分失敗に備え、取得できた銘柄コードのみ DELETE → INSERT により置換（冪等性確保）。
    - テスト用に _call_openai_api を patch 可能（ユニットテスト容易化）。
    - タイムウィンドウ計算 util（calc_news_window）を提供（JST 基準の前日 15:00 ～ 当日 08:30 相当を UTC naive datetime で返す）。
    - public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp の calc_news_window で取得するウィンドウからマクロキーワードをフィルタしてタイトルを抽出。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを JSON で取得し、クリップ・合成してスコア化。
    - API 失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、失敗時は ROLLBACK を実施して例外を上位に伝播。
    - public API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

- データモジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定・検索ロジック:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にカレンダーがない場合は曜日（土日）ベースのフォールバックを採用。
    - 最大探索範囲を設定して無限ループを防止。
    - 夜間バッチ job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアント経由で差分取得 → 保存（jq.save_market_calendar）を行う。バックフィルと健全性チェックを実装。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETL の結果を表すデータクラス ETLResult を公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を組み合わせる設計方針を実装。
    - デフォルトの backfill 日数や calendar lookahead などの定数を定義。
    - ETLResult は to_dict() を備え、quality_issues は dict に変換して出力可能。

- 研究（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum(conn, target_date)：1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)：20日 ATR（atr_20）・相対 ATR（atr_pct）・20日平均売買代金（avg_turnover）・出来高比率（volume_ratio）を計算。欠損時は None。
    - calc_value(conn, target_date)：raw_financials から最新財務（eps, roe）を取得し PER/ROE を算出。EPS が 0 または欠損の場合は per を None にする。
    - DuckDB を活用した SQL ベースの実装。外部 API へはアクセスしない（安全）。

  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None)：指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。引数検証（horizons は 1..252 の正整数）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンのランク相関（IC）を実装。有効レコード 3 未満で None を返す。
    - rank(values)：同順位は平均ランクを返すランク関数（float の丸めで ties を安定化）。
    - factor_summary(records, columns)：カウント・平均・標準偏差・最小・最大・中央値を計算。None 値除外。

- その他
  - OpenAI SDK（openai.OpenAI）を使用する実装（依存）。
  - DuckDB を主要なローカル DB として使用する設計（依存）。
  - ロギングを各モジュールで活用し、情報・警告・例外を適切に出力する設計。

### 変更（設計上の注記）
- ルックアヘッドバイアス回避:
  - score_news / score_regime / ファクター計算など、内部実装は datetime.today() / date.today() を使わず、呼び出し元から target_date を与える形式で設計。
  - DB クエリは target_date 未満／以前等の排他条件を付けてルックアヘッドを防止。

### 修正
- （初期リリースのため過去修正なし）

### 既知の制約・注意点
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要あり。未指定時は ValueError を送出。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用する想定だが、外側に余計なテキストが混ざる可能性に対してはパーサ側で復元処理を行う（最外の {} を抽出）。
- DuckDB の executemany は空リストを受け付けないバージョン（0.10 等）への互換性に配慮した処理が含まれる。
- .env パーシングは POSIX シェルの .env の一般的な慣習に近いが、完全互換を保証するものではない。
- monitoring / execution / strategy の具体的な実装はこのリリース時点ではパッケージエントリポイントとして公開しているが、機能の追加や外部 API 連携は今後のリリースで拡張予定。

---

今後のリリースでは、運用（execution）・監視（monitoring）・戦略（strategy）の実践的な実装、テストカバレッジの強化、ドキュメントとサンプル ETL ワークフローの追加などを予定しています。