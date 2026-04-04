# Changelog

すべての重要な変更履歴はここに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

※ このファイルはコードベースから推測して作成しています（実装の説明・設計意図を含む）。

## [0.1.0] - 2026-04-04

### Added
- 基本パッケージ公開
  - パッケージルート: `kabusys`（`__version__ = "0.1.0"`）。
  - サブパッケージのエクスポート: `data`, `strategy`, `execution`, `monitoring`。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - .env パーサ実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート外で直前が空白またはタブの `#` をコメントとして扱う）。
  - 環境変数保護機能（読み込み時に既存 OS 環境変数を保護）。
  - `Settings` クラスによるプロパティ提供（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境判定など）。
  - 必須環境変数未設定時は `_require` により `ValueError` を送出。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得して `ai_scores` テーブルへ書き込み。
  - 時間ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
  - バッチ処理:
    - 同時に処理する銘柄数: 最大 20（_BATCH_SIZE）。
    - 1銘柄あたり最大記事数: 10（_MAX_ARTICLES_PER_STOCK）。
    - 1銘柄あたり最大文字数トリム: 3000（_MAX_CHARS_PER_STOCK）。
  - エラー耐性:
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（最大リトライ回数 configurable: _MAX_RETRIES）。
    - 失敗時は当該チャンクをスキップし、他銘柄の処理を継続（フェイルセーフ設計）。
  - レスポンス検証:
    - JSON パース、`results` リスト存在、各要素に `code` と `score` を持つか等を検証。
    - スコアは ±1.0 にクリップ。
    - JSON mode でも前後に余計なテキストが混入する場合に備え最外側の `{...}` を抽出して復元する耐性処理あり。
  - DuckDB 互換性考慮:
    - `executemany` に空リストを渡さない（DuckDB 0.10 の制約回避のため）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（`bull` / `neutral` / `bear`）を判定し `market_regime` テーブルへ冪等書き込み。
  - MA200 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
  - マクロニュースは `news_nlp.calc_news_window` で算出したウィンドウからタイトルを取得し、OpenAI に投げて `macro_sentiment` を算出。記事がない場合は LLM 呼び出しを行わず `0.0` を返す。
  - API 呼び出し失敗時は `macro_sentiment=0.0` にフォールバックし継続（ログ出力）。レスポンスの JSON パース失敗や想定外応答も同様のフォールバック。
  - OpenAI クライアント生成は `OpenAI(api_key=...)`。デフォルトモデル: `gpt-4o-mini`、JSON mode を使用。
  - レートリミット・ネットワーク障害等でのリトライ・バックオフ実装あり。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダー取得/保存バッチ（`calendar_update_job`）。
    - 営業日判定ユーティリティ:
      - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - 設計方針:
      - DB の `market_calendar` が未取得または該当日が未登録の場合は曜日ベース（平日を営業日）でフォールバック。
      - 探索の上限日数（_MAX_SEARCH_DAYS）を設け、無限ループを防止。
      - バックフィル期間（_BACKFILL_DAYS）を設け、API 側の訂正を取り込む。
  - ETL パイプライン（pipeline / etl）:
    - 差分更新・保存・品質チェックを行う ETL のインターフェース。
    - `ETLResult` データクラスを導入:
      - `target_date`, 取得/保存数、`quality_issues`, `errors` 等を格納。
      - `has_errors`, `has_quality_errors`, `to_dict` 等のユーティリティを提供。
    - デフォルトのバックフィル日数や最小データ開始日などの定数を定義。

- リサーチ / ファクター計算（kabusys.research）
  - 主要なファクター計算を提供し Research 用 API として公開:
    - `calc_momentum`:
      - 1M/3M/6M リターン（営業日ベース）と MA200 乖離率（データ不足時は None / MA200 データが 200 行未満なら None）。
    - `calc_volatility`:
      - 20日 ATR（平均）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）等。
    - `calc_value`:
      - PER（株価 / EPS、EPS が 0 または NULL の場合は None）、ROE（raw_financials から取得）。
    - `calc_forward_returns`:
      - 将来リターン（任意ホライズン）を一度のクエリで計算。ホライズンの妥当性チェックあり（1〜252）。
    - `calc_ic`, `rank`, `factor_summary`:
      - IC（Spearman の ρ）計算、同順位の平均ランク処理、基本統計量（count/mean/std/min/max/median）。
  - 設計方針:
    - DuckDB 接続を受け取り、DB 内テーブルのみ参照する（発注や外部 API にアクセスしない）。
    - ルックアヘッドバイアスを避けるため `datetime.today()` 等を参照しない。

### Changed
- （初版）コードベースの設計方針やフェイルセーフ、テスト容易性の明確化を反映。
  - OpenAI 呼び出し箇所に差し替え（テスト用 patch）可能な内部ラッパーを用意（`_call_openai_api`）し、モジュール間でプライベート関数を共有しない設計。

### Fixed
- （初版）DuckDB の互換性問題に対する回避策を実装:
  - `executemany` に空リストを渡さないように条件分岐を追加（DuckDB 0.10 の制約対応）。

### Notes
- 必須となる可能性のある環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（OpenAI 呼び出し時）、その他 Settings が参照するキー。
- OpenAI の応答は厳密な JSON を想定しているが、実運用ではパース失敗や API エラーが発生する前提でフォールバック処理を備えている（ゼロスコアやスキップ）。
- DB 側の前提テーブル（存在が期待されるテーブル名の例）:
  - `prices_daily`, `raw_news`, `news_symbols`, `ai_scores`, `market_regime`, `market_calendar`, `raw_financials` 等。
- 日時取り扱いはすべて日時のルックアヘッドを避ける方針（関数に target_date を渡す仕様）。
- OpenAI モデルはコード内で `gpt-4o-mini` を指定。将来的な SDK 変更（例: 例外クラスのフィールド名変更）にも耐性を持つ実装になっている（`getattr` 等で安全に値取得）。

### Security
- 特になし（初版）。

---

過去のバージョンや将来の変更はここに追記してください（例: [Unreleased] セクションの追加等）。