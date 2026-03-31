# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

※ バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [0.1.0] - 2026-03-31

Added
- パッケージ初期リリース。日本株自動売買システムの基盤モジュール群を追加。
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能を追加（プロジェクトルート判定: .git または pyproject.toml）。
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの扱い等に対応した .env パーサを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数を保護する protected 機構、override フラグにより .env.local で上書き可能。
  - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等を取得）。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を取得。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数/文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用したレスポンス検証（results 配列, code, score の妥当性チェック）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ。
    - DuckDB への冪等書き込み（該当 date の該当コードのみ DELETE → INSERT）を実装。
    - フェイルセーフ: API 失敗時はそのチャンクをスキップし、全体処理を継続。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - prices_daily と raw_news を参照、calc_news_window を利用してマクロ記事を抽出。
    - OpenAI API 呼び出しは専用の内部実装（テスト時には差し替え可能）。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの有無・内容を考慮した営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックを実装。
    - 最大探索日数の上限（_MAX_SEARCH_DAYS）など無限ループ防止の保護を実装。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - 差分取得・保存・品質チェックの流れに基づく ETLResult（dataclass）を公開。
    - DB の最終日確認、バックフィル、J-Quants クライアント経由の保存、品質チェック結果の集約を設計。
    - DuckDB に対するテーブル存在チェックや最大日付取得ユーティリティを実装。
    - ID 列挙的な保存（ON CONFLICT/冪等）や、部分失敗時にも既存データを保護する設計方針を反映。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）を計算する関数を追加。
    - DuckDB に対する SQL ベースの実装で、データ不足時の None 扱い・ログ出力を実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、ホライズン指定可能）、IC（calc_ic：Spearman ランク相関）、ランク変換ユーティリティ、ファクター統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず標準ライブラリで実装。
  - 研究用ユーティリティの再エクスポート（zscore_normalize など）。

- 共通事項
  - DuckDB を主要データストアとして使用する設計。テーブル存在チェックや日付型の扱いなど DuckDB 互換性を考慮。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない設計（target_date 引数を基準に処理）。
  - ロギングによる状態・フェイルセーフの明瞭化（各種 WARN/INFO/DEBUG ログあり）。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Security
- 初版リリースのため該当なし。

Notes / Migration
- OpenAI を利用する機能（score_news, score_regime）を使うには OPENAI_API_KEY を環境変数に設定するか、各関数に api_key を渡してください。未設定時は ValueError を発生します。
- .env 自動読み込みはプロジェクトルート検出に依存します。パッケージ配布後の挙動を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）は事前に作成／データ投入が必要です（ETL パイプラインや jquants_client を利用して初期ロードしてください）。
- News / Regime の LLM 結果は JSON 形式を期待します。LLM の変化による出力差分はバリデーションで部分的に安全化していますが、運用時は OpenAI レスポンスに注意してください。

Known issues / Limitations
- OpenAI 呼び出しは外部 API に依存するため、API 仕様や料金・レート制限に影響を受けます。高頻度運用時はレート管理が必要です。
- ai.news_nlp の executemany は DuckDB のバージョン差での挙動に依存するため、空パラメータ時の分岐（空リスト回避）を実装していますが、利用する DuckDB バージョンでの動作確認を推奨します。
- 一部の API 呼び出し・DB 書き込みは例外を上位へ伝播します（例：DB 書き込み失敗）。運用バッチでは呼び出し側での例外ハンドリングを推奨します。

Authors / Contributors
- 本リリースはコードベース内のドキュメンテーションとソース実装に基づいて作成されました。詳細は各モジュールの docstring を参照してください。