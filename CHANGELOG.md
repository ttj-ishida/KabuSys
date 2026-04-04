# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
現在の日付: 2026-04-04

## [0.1.0] - 2026-04-04
最初の公開リリース。以下の主要機能と実装を含みます。

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。公開ライブラリの初期実装。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロード優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env 行パーサを実装（コメント行、export プレフィックス、クォート内エスケープ、インラインコメント処理対応）。
  - 上書き挙動（override）と保護された OS 環境変数（protected）の考慮。
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / システム環境等のプロパティを安全に取得・検証。
    - KABUSYS_ENV・LOG_LEVEL の検証（許容値チェック）。
    - Path 型プロパティ（duckdb, sqlite, pid 等）に expanduser を適用。

- AI: ニュースNLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチで送信してセンチメント（ai_score）を算出する処理を実装。
  - ニュースウィンドウの計算（JST 基準）を calc_news_window として提供。
  - 1 銘柄あたりの記事数/文字数上限（トリム）を導入しトークン肥大を抑制。
  - API 呼び出しのリトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフ）を実装。
  - OpenAI の JSON Mode を利用し、レスポンスのバリデーション・復元処理（余分な前後テキストが混入した場合の {} 抽出）を実装。
  - スコアは ±1.0 にクリップ。取得したスコアのみを ai_scores テーブルへ冪等 (DELETE → INSERT) で書き込み（部分失敗時の既存スコア保護）。
  - バッチサイズ、リトライ回数、最大文字数等の定数を定義して挙動を制御。

- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - MA200 乖離の計算（_calc_ma200_ratio）では target_date 未満のデータのみを使用し、データ不足時は中立（1.0）にフォールバック。
  - raw_news からマクロキーワードに一致するタイトルを抽出して LLM に渡す処理を実装（最大件数制限あり）。
  - OpenAI 呼び出しのリトライ・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - 合成スコアのクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - OpenAI クライアントの注入（api_key 引数または環境変数 OPENAI_API_KEY）をサポート。

- 研究用モジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードを target_date 以前の最新として取得）。
    - DuckDB 内で SQL ウィンドウ関数を活用した効率的な実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズンの将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満は None を返す。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - 研究 API を __init__ で再エクスポートし、主要関数を公開。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを利用した営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日（週末）ベースのフォールバックを採用し、まばらな DB データでも一貫した結果を返す設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等で更新するバッチ処理を実装（バックフィル・健全性チェックを含む）。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開し、ETL 実行結果（取得件数、保存件数、品質問題、エラー）を構造化して返却可能に。
    - pipeline モジュールの ETLResult を再エクスポート（kabusys.data.etl）。
    - ETL 設計方針: 差分更新、バックフィル、品質チェック（quality モジュールとの連携）などを意図した設計。

- 共通設計方針・実装ノート
  - DuckDB を主要なローカル分析 DB として利用する設計。
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を内部ロジックで参照せず、必ず外部から target_date を受け取る実装方針を採用（AI スコアやファクター計算など）。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT / ON CONFLICT 想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンス検証・復元・クリップ・部分失敗の保護を行う。

### 変更
- 初版のため該当なし。

### 修正
- 初版のため該当なし。

### 非推奨
- 初版のため該当なし。

### 削除
- 初版のため該当なし。

### セキュリティ
- 初版のため該当なし。

注意:
- 本リリースはライブラリの初期実装であり、OpenAI/API キーや DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）の事前準備が必要です。
- 実行時のログや例外メッセージは内部のロギング方針に基づき詳細に出力されます。API 呼び出し失敗時はフェイルセーフ（スコア 0.0、部分スキップ）で継続する設計になっています。