# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、リポジトリ内のソースコードから推測して作成した初期の変更履歴です。

全般的な注意
- 日付は本コードスナップショットの現時点（2026-03-31）を使用しています。
- 多くの設計方針（ルックアヘッドバイアス回避、DuckDB 互換性、冪等書き込み、OpenAI 呼び出しの堅牢化など）がソース内コメントで明示されています。
- テスト容易性のために一部内部関数（例: OpenAI 呼び出し）はモック差し替え可能に実装されています。

[0.1.0] - 2026-03-31
----------------------------------------

Added
- パッケージ初期公開
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を含める。

- 環境設定・ロード機能 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env 行パーサーで以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなしのインラインコメント（'#' の直前が空白/タブの場合）
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）とデフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）を簡単に取得できるようにした。
  - 環境変数の検証:
    - KABUSYS_ENV は development / paper_trading / live のいずれかのみ許容。
    - LOG_LEVEL の値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - 各種システムフラグや監視閾値（CPU/MEM/DISK）を環境変数で設定可能。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント解析 (kabusys.ai.news_nlp)
    - raw_news と news_symbols を使用し、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON mode で一括センチメント評価を行う処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄処理（_BATCH_SIZE = 20）。
    - 1 銘柄あたりの最新記事最大数と文字数を制限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）してトークン肥大化を抑制。
    - リトライ戦略: 429（RateLimit）・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ（最大試行回数制御）。
    - レスポンスの厳格なバリデーション: JSON 抽出、"results" 配列、各要素の code/score 検証、数値の有限性チェック、スコアの ±1.0 クリップ。
    - 成功した銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）し、部分失敗時に他銘柄の既存データを保護。
    - API キー未設定時は ValueError を送出。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタしてタイトルを抽出し、OpenAI（gpt-4o-mini, JSON mode）に渡して macro_sentiment を取得。
    - ルックアヘッドバイアス防止のため、prices_daily のクエリは target_date 未満のみを参照し、関数は datetime.today()/date.today() を使わない設計。
    - API 呼び出しはリトライ処理を備え、失敗時は macro_sentiment=0.0 にフォールバックして処理を継続（例外は上げない）。
    - market_regime テーブルへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - API キー未設定時は ValueError を送出。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを元に営業日判定、次/前営業日取得、期間の営業日リスト取得、SQ日判定などのユーティリティを実装。
    - DB にデータがない場合は曜日ベースでフォールバック（土日は非営業日）。
    - calendar_update_job を実装し、J-Quants API からの差分取得 → market_calendar へ冪等保存（バックフィル・健全性チェックを含む）を行う。
    - 最大探索日数やバックフィル日数、先読み日数等の安全パラメータを定義。

  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult dataclass を公開し、ETL の取得件数・保存件数・品質問題・エラー一覧を保持、辞書化して監査ログに使えるように実装。
    - ETL の設計方針として差分更新・バックフィル・品質チェック（quality モジュール呼び出し想定）・id_token 注入によるテスト容易性を明記。
    - DuckDB 互換性を考慮したテーブル存在チェック等のユーティリティを実装。
    - jquants_client を経由してデータ取得/保存を行う想定（jquants_client は別モジュール）。

- 研究/因子解析（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を算出。データ不足時に None を返す設計。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials の最新財務データと価格を組み合わせて PER / ROE を算出（EPS が 0 または欠損の場合は None）。
    - すべて DuckDB 接続を受け取り SQL ベースで実行し、本番発注等にはアクセスしないことを明記。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン最大値に応じたスキャン範囲制限あり。
    - calc_ic: スピアマンのランク相関（IC）を計算。データ不足（有効レコード < 3）時は None を返す。
    - rank: 同順位は平均ランクで処理するランク関数を提供（丸めで ties を検出しやすくしている）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティを実装。
  - zscore_normalize は kabusys.data.stats モジュールから再利用している旨の公開。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security / Operational notes
- OpenAI API は gpt-4o-mini を想定、JSON mode（response_format={"type":"json_object"}）を使用するため、レスポンスパース時の回復ロジックや厳格なバリデーションを備えている。
- .env の自動読み込みは実行環境の OS 環境変数を保護するため、既存の環境変数は既定では上書きしない。OS 環境変数の保護セットは読み込み時に snapshot される。
- DuckDB のバージョン依存（executemany に空リストを渡せない等）に配慮した実装を行っている。
- Slack / Kabu API / J-Quants などのサードパーティ設定は必須で、Settings クラスのプロパティから取得できる（未設定時はエラーとなる項目あり）。

Known issues / Notes
- kabusys.data.pipeline モジュール内の一部実装がスナップショットの末尾で途切れているように見えます（_get_max_date の戻り処理付近が不完全）。実行環境で利用する際は該当メソッドの最終実装を確認してください。
- パッケージの __all__ に strategy, execution, monitoring が含まれていますが、このスナップショットにはそれらのサブモジュールの完全実装が含まれていない可能性があります（リポジトリの他箇所を参照してください）。
- OpenAI 呼び出しや外部 API 呼び出しは実行コストとレイテンシに影響するため、本番運用では API キー管理・レート制御・コスト監視が必要です。

その他
- 各モジュール内に設計方針やフェイルセーフの振る舞いが明記されており、テスト容易性（内部 API のモック差し替え）やルックアヘッドバイアス回避に配慮した実装になっています。運用前に必ず設定ファイル（.env.example）や DB スキーマ（ai_scores, raw_news, prices_daily, market_calendar 等）を確認してください。