# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリース日付は YYYY-MM-DD 形式で記載します。  
- すべての変更はカテゴリ（Added / Changed / Deprecated / Removed / Fixed / Security）ごとに整理します。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、公開モジュール例: data, strategy, execution, monitoring を __all__ に定義。
  - バージョン情報: __version__ = "0.1.0" を追加。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数の読み込みを提供。プロジェクトルート（.git または pyproject.toml）を基準に自動検出して .env / .env.local を読み込む。
  - .env パーサ実装（引用文字列のエスケープ・インラインコメント処理・export KEY=VALUE 形式に対応）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
  - OS 環境変数を保護する機構（.env.local による上書き挙動の保護）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / ログレベル / 環境（development/paper_trading/live）などのプロパティを取得可能。
  - 必須環境変数未設定時に ValueError を送出する _require 関数を実装。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込み。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - エラー時はフォールバック（スキップ）し、部分失敗でも既存スコアを保護するためコード単位で DELETE → INSERT を実行。
    - リトライ実装（429/ネットワーク断/タイムアウト/5xx 対象、指数バックオフ）。
    - calc_news_window: ニュース収集ウィンドウ（JST基準 → UTC変換）を提供。

  - regime_detector.score_regime
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定して market_regime テーブルに冪等書き込み。
    - LLM 呼び出しは独立実装（news_nlp と内部関数を共有しない設計）。
    - API 呼び出し失敗時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI クライアント呼び出しとリトライ・エラーハンドリングを実装。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダーを扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末＝非営業日）をサポート。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存する夜間バッチジョブを実装（バックフィル・健全性チェック含む）。
    - 最大探索日数やバックフィル日数等の安全パラメータを定義（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。

  - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを追加（取得数・保存数・品質チェック結果・エラー集約などを保持）。
    - 差分更新、品質チェック（quality モジュールと連携）、id_token 注入可などの設計方針に沿った基盤処理を実装。
    - jquants_client を利用した保存処理の呼び出しを想定。

- Research（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）およびバリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials のみを参照する設計で、本番取引系へのアクセスは行わない。
    - データ不足時の挙動（None を返す）を明確に実装。

  - feature_exploration
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）、IC（calc_ic: スピアマンのランク相関）、ランク変換（rank）および統計サマリー（factor_summary）を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリで実装。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし（ただし堅牢性を考慮した多数のフェイルセーフとフォールバック対応を実装）。
  - OpenAI API 呼び出しに対するリトライ/backoff を実装し、一部エラーでプロセス全体が停止しないように設計。
  - .env パーサにおいて引用符内のエスケープやインラインコメントの取り扱いを改善。

### Deprecated
- 該当なし。

### Removed
- 該当なし。

### Security
- OpenAI API キー（OPENAI_API_KEY）や各種トークンは環境変数で管理する想定。Settings の必須項目未設定時は ValueError を送出するため、実行時に適切な環境変数管理が必要。
- .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途など）。

---

注記 / 設計方針（主要点）
- ルックアヘッドバイアスの排除: AI / ETL / Research 処理は内部で datetime.today() / date.today() に依存せず、明示的な target_date を受け取る設計。
- DuckDB を主要ストレージとして想定し、SQL と Python を組み合わせて計算を行う。
- DB 書き込みは可能な限り冪等性を担保（DELETE→INSERT、ON CONFLICT 等）している。
- 部分失敗時の安全性: API 失敗やパース失敗時は例外で全停止させず、警告ログを出してフェイルセーフなフォールバックを行う（ただし、重大な DB 書き込み失敗は上位へ例外を伝播）。

もし CHANGELOG に追記したい細かな変更点やリリース日を別に指定したい場合は教えてください。