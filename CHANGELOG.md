CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日はリポジトリの現行日付を使用しています。

[Unreleased]
------------

- 次回リリースに向けた未確定の変更はここに記載します。

[0.1.0] - 2026-04-04
-------------------

初回公開リリース。

Added
- 基本パッケージ初期構成を追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、公開 API (__all__) を定義。
- 環境変数 / 設定管理モジュールを追加 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数からの自動読み込み機能を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の柔軟なパース実装（export プレフィックス対応、クォート内のエスケープ、行末コメントの取扱いなど）。
  - Settings クラスでアプリケーション設定をプロパティで提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、DB パス、監視設定、閾値、環境判定・ログレベル等）。
  - 必須環境変数未設定時の明確なエラー (_require) を提供。
- AI（自然言語処理）モジュールを追加 (kabusys.ai)
  - news_nlp モジュール (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）にバッチ（最大 20 銘柄）で投げてセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ保存する処理を実装。
    - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）計算関数 calc_news_window を提供。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）や指数バックオフ、結果の厳密な JSON バリデーション、スコアの ±1 クリップを実装。
    - DuckDB の executemany に対する互換性を考慮した空リスト処理（空パラメータは送らない）。
  - regime_detector モジュール (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする score_regime を実装。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）等を実装。
    - ルックアヘッドバイアス対策（datetime.today() を内部参照しない、DB クエリの排他条件）を設計思想として明示。
- Research（調査/因子）モジュールを追加 (kabusys.research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の算出（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等を算出。
    - calc_value: raw_financials から EPS/ROE を利用して PER/ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL ベースの実装で外部 API にアクセスしない設計。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン先の将来リターン（LEAD を利用）を一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 未満は None）。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計要約。
- Data（データプラットフォーム）モジュールを追加 (kabusys.data)
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants クライアント経由の夜間バッチ更新 calendar_update_job を実装（バックフィル、健全性チェック、冪等保存）。
    - DB 未登録日の曜日ベースフォールバック実装（DB 値が存在する場合は DB を優先）。
  - pipeline / etl
    - ETLResult データクラス（ETL 実行の計測・監査用）を公開（kabusys.data.etl 再エクスポート）。
    - pipeline モジュールの下で ETL の設計（差分取得、保存、品質チェック）を実装するための基盤を提供。
- 例外処理・ロギング・フェイルセーフ
  - OpenAI API 呼び出しや外部取得に対して堅牢なリトライロジック、タイムアウト、警告ログ及びフォールバック（ゼロ値やスキップ）を多数実装。
  - DB 書き込みは明示的に BEGIN / DELETE / INSERT / COMMIT を行い、失敗時は ROLLBACK を試みて例外を再送出する（冪等性確保）。
- DuckDB との互換性考慮
  - executemany の空リスト問題への対処（空の場合は実行をスキップ）など、DuckDB の実装差分へ対応。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- OpenAI API キーの取り扱い
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY のいずれかが必要。未設定時は ValueError を送出して明示的に失敗する設計。
- 環境変数の上書き保護
  - .env 読み込み時、既存 OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Usage hints
- ルックアヘッドバイアスを防ぐ設計
  - AI スコアリングやレジーム判定関数は内部で datetime.today()/date.today() に頼らず、必ず外部から target_date を受け取る。
- ローカルテスト
  - 自動 .env ロードをオフにしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のバージョン差異
  - executemany に空配列を渡せないバージョンを想定したチェックが入っています（空パラメータでは INSERT/DELETE を実行しません）。
- OpenAI 呼び出しの差し替え
  - テスト容易性のため各モジュール内の _call_openai_api を unittest.mock.patch で差し替え可能。

作者注
- 各モジュールには詳細な設計意図・フェイルセーフ挙動・互換性ノートが docstring に記載されています。実運用前に設定（環境変数、DB 初期スキーマ、API キー等）の確認を推奨します。