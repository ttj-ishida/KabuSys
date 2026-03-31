CHANGELOG
=========

すべての重要な変更点をここに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット規約:
- 変更はカテゴリ（Added / Changed / Fixed / Security / Notes）で分類しています。
- 各リリースにはバージョンと日付を付与しています。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-03-31
-----------------

概要:
- 初期リリース。日本株自動売買フレームワーク「KabuSys」のコア機能群を提供します。
- 主にデータ取得/管理、リサーチ（ファクター計算）、ニュースNLP、マーケットレジーム判定、環境設定ユーティリティを含みます。

Added
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ に __version__ = "0.1.0" と __all__ を定義。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイル自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env のパースは export 形式、クォート、エスケープ、インラインコメントに対応する堅牢な実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB / システム関連の設定値をプロパティで取得。
  - 必須環境変数が未設定の場合は明確な ValueError を発生させる。

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントスコアを生成し ai_scores に書き込む。
  - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
  - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄、記事数/文字数の上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 再試行戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
  - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
  - テスト容易性: _call_openai_api をテストでパッチ可能（unittest.mock.patch の想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime に冪等書き込み。
  - マクロキーワードベースで関連ニュースを抽出し、OpenAI による JSON 出力で macro_sentiment を算出。
  - API エラー時はフェイルセーフとして macro_sentiment = 0.0 を採用（例外を上位に投げず継続）。
  - レジームスコア合成ロジック（クリップ・閾値）を実装。
  - API 呼び出しの再試行処理・5xx 判定など堅牢なエラーハンドリングを実装。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得し PER / ROE を計算。
    - 各関数は DuckDB SQL を用いて高速に計算し、データ不足時は None を返すことで明示的に扱えるように設計。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（例: 翌日/翌週/翌月）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算。
    - rank(values): 平均ランク（同順位は平均）を返すユーティリティ。
    - factor_summary(records, columns): 各ファクターの基本統計量（count/mean/std/min/max/median）を算出。
  - 依存は標準ライブラリと DuckDB のみ（pandas 等に依存しない実装）。

- データ / カレンダー管理（kabusys.data）
  - calendar_management:
    - market_calendar を基にした営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーが存在しない場合は曜日ベースのフォールバック（平日のみ営業日）。
    - 夜間バッチ: calendar_update_job(conn, lookahead_days=90) で J-Quants から差分フェッチして market_calendar を冪等保存。バックフィルや健全性チェックを実装。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) による無限ループ防止。
  - pipeline:
    - ETLResult dataclass を導入（ETL の各種メトリクス、品質チェック結果、エラー概要を保持）。
    - ETL パイプライン用の各種ユーティリティ（テーブル存在チェック、最大日付取得など）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは関数引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY でも指定可能。どちらも未設定の場合は ValueError を発生させ明示的に失敗。
- .env 自動ロード時に OS 環境変数は protected として上書きから保護（.env.local は override を許可するが、既存 OS 環境変数は上書きされない）。
- .env 読み込みで失敗した場合は警告を出力して処理を継続（安全優先）。

Notes / 注意点
- ルックアヘッドバイアス防止: 各モジュールは datetime.today() / date.today() をスコープ外で参照せず、必ず引数で target_date を受け取る設計。
- DuckDB の互換性: executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮した実装（空チェックを行ってから executemany）。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を使用。稀に余計な前後テキストが混ざるケースに備え JSON 抽出ロジックを実装。
- テスト支援: OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、テスト時は patch して差し替え可能。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI 機能を利用する場合）
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

将来の改善案（言及）
- ai レイヤのモデルやバッチサイズ等のパラメータ化（現状は定数定義）。
- news_nlp のレスポンス検証ルールの拡張（より細かいエラー分類、スキーマ検証）。
- calendar_update_job の J-Quants クライアントの差し替え容易性向上（テスト用モック注入）。

ライセンスや貢献方法等はリポジトリの README / CONTRIBUTING を参照してください。