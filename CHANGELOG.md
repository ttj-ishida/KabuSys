# Changelog

すべての注目すべき変更をこのファイルに記載します。本プロジェクトは Keep a Changelog の慣習に従います。  
予備知識: 本 CHANGELOG は、提示されたコードベースの内容から実装された機能・設計上の要点・重要な挙動を推測して記載したものです。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-27

Added
- パッケージ初期リリース。
- パッケージ名: kabusys、バージョン 0.1.0。
- モジュール群の追加（主要機能）:
  - 環境設定管理 (kabusys.config)
    - .env/.env.local 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env の堅牢なパーサ実装（export 付き、シングル/ダブルクォート、エスケープ、インラインコメント判定の扱い）。
    - Settings クラス公開（J-Quants / kabu API / Slack / DB パス / 環境名 / ログレベル 等のプロパティ）。
    - 必須環境変数が未設定の場合に ValueError を送出する _require 実装。
    - env ロジックで allowed 値チェック（development, paper_trading, live）やログレベル検証。
  - AI 関連 (kabusys.ai)
    - ニュース NLP スコアリング (kabusys.ai.news_nlp.score_news)
      - raw_news / news_symbols を集約して銘柄ごとのニュース文を作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
      - バッチ処理（最大 20 銘柄/回）、1 銘柄あたり記事数/文字数制限、JSON Mode を用いた堅牢なパース。
      - 429・ネットワーク断・タイムアウト・5xx について指数バックオフでリトライ。非再試行系のエラーはスキップして継続。
      - レスポンスのバリデーション（results 配列、code/score の存在、既知コードだけ採用、スコアは ±1 にクリップ）。
      - スコアは ai_scores テーブルへ冪等的に書き込み（該当コードのみ DELETE → INSERT）。
      - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計。
      - OpenAI API キーは引数か環境変数 OPENAI_API_KEY から解決。未設定なら ValueError を送出。
    - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
      - ニュースは news_nlp.calc_news_window を使って取得し、LLM へのリクエストは専用の呼び出し実装を使用（モジュール結合を避ける）。
      - API エラー時は macro_sentiment=0.0 のフェイルセーフ、スコアは -1..1 にクリップ。
      - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
  - データ基盤（kabusys.data）
    - カレンダー管理 (kabusys.data.calendar_management)
      - market_calendar を利用した営業日判定機能: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
      - market_calendar が未取得の場合は曜日ベース（土日除外）のフォールバック。
      - 夜間バッチ calendar_update_job: J-Quants から差分取得、バックフィル（直近 _BACKFILL_DAYS 日）・健全性チェック（極端に未来日が存在する場合はスキップ）・保存処理を実装。
    - ETL パイプライン (kabusys.data.pipeline)
      - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー一覧などを格納）。
      - 差分取得ロジック、バックフィル動作、品質チェック連携（quality モジュール）を想定した設計。
    - ETL インターフェース再公開 (kabusys.data.etl)
      - pipeline.ETLResult を再エクスポート。
    - DuckDB を想定した SQL 実装（各処理は DuckDB 接続を受け取り SQL クエリで処理）。
  - リサーチ / ファクター分析 (kabusys.research)
    - factor_research モジュール
      - モメンタム、ボラティリティ（ATR等）、バリュー（PER/ROE）等のファクターを prices_daily / raw_financials を参照して計算する関数群: calc_momentum, calc_volatility, calc_value。
      - 計算は DuckDB のウィンドウ関数や SQL を活用し、データ不足時は None を返す等の堅牢化。
    - feature_exploration モジュール
      - 将来リターン計算 calc_forward_returns（複数ホライズン対応、horizons のバリデーションあり）。
      - IC（Spearman の ρ）を算出する calc_ic、ランク変換 util rank、ファクター統計 summary を計算する factor_summary。
      - pandas 等に依存しない純粋 Python 実装設計。
  - パッケージエクスポート
    - top-level __init__ で version と公開サブパッケージを定義 (__version__ = "0.1.0")。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。
- 注意: OpenAI API キーや各種トークンは環境変数を介して扱う設計。環境変数の管理には十分注意してください。

Notes / 設計上の重要ポイント（覚書）
- ルックアヘッドバイアス防止: AI モジュールおよびリサーチ系は内部で現在日時を直接参照しない設計（target_date ベースで計算）。
- フェイルセーフ: OpenAI API 呼び出しや外部 API エラー時は例外を破壊的に上げず、デフォルト値（例: macro_sentiment=0.0）で継続する箇所がある（但し、API キー未設定は ValueError で明示）。
- 冪等性・トランザクション: DB への書き込みは DELETE → INSERT の置換や BEGIN/COMMIT/ROLLBACK を用いた冪等性保持を意識した実装。
- DuckDB 互換性考慮: executemany の空リスト回避、日付型変換ユーティリティ等、DuckDB の挙動に合わせた実装上の注意点あり。
- OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を使用。レスポンスパース失敗に対する復元ロジックも実装。

Acknowledgements
- この CHANGELOG は提示されたソースコードから実装内容・設計方針を推測して作成しています。実際のリリースノートとして公開する際は、開発履歴（コミットログ、リリース日、既知の制限や互換性情報など）を合わせて確認・追記してください。