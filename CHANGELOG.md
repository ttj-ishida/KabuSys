# Changelog

すべての重要な変更点を Keep a Changelog の形式に従って日本語で記載します。

## [0.1.0] - 2026-03-31

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ公開情報
    - パッケージトップ: src/kabusys/__init__.py にてバージョン __version__="0.1.0"、公開モジュール data, strategy, execution, monitoring を定義。

- 環境設定 / ロード機能 (src/kabusys/config.py)
  - .env および .env.local の自動読み込み実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に検索（__file__ 起点で CWD に依存しない）。
  - .env パーサ: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、無効行スキップ等をサポートする堅牢な行パーサを実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 でスキップ可能。
  - Settings クラスでアプリケーション設定をラップ:
    - J-Quants / kabuAPI / Slack / DB パス（duckdb/sqlite）などの取得プロパティを提供。
    - 必須環境変数未設定時は ValueError を投げる _require 実装。
    - KABUSYS_ENV の検証（development, paper_trading, live）と LOG_LEVEL 検証を実装。
    - is_live/is_paper/is_dev の便宜プロパティ。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 時間ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で扱う）を明文化し calc_news_window を提供。
    - バッチサイズ、文字数/記事数トリム: _BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000 を導入。
    - JSON Mode の利用とレスポンス検証: results 配列の構造・型チェック、未知コードは無視、数値でないスコアはログ警告してスキップ。
    - 再試行戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフ（最大リトライ回数 _MAX_RETRIES）を実装。
    - フェイルセーフ: API 呼び出し失敗時は当該チャンクをスキップ、全体でスコア取得銘柄数が 0 の場合は処理失敗として 0 を返す。
    - DuckDB 互換性考慮: executemany に空リストを渡さないガード（DuckDB 0.10 の挙動に対応）。
    - テスト用フック: _call_openai_api を patch 可能にしてユニットテスト容易性を確保。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードリストによる raw_news のフィルタリング、最大記事件数制限、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得。
    - API 障害時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 冪等書き込み: market_regime テーブルへ BEGIN / DELETE / INSERT / COMMIT の形式で日付単位の上書きを行う。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

- データプラットフォーム / ETL (src/kabusys/data)
  - ETL の型エクスポート (src/kabusys/data/etl.py)
    - pipeline.ETLResult を再エクスポート（外部利用用）。
  - ETL パイプラインの基礎 (src/kabusys/data/pipeline.py)
    - ETLResult dataclass を定義（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装するためのユーティリティを提供（テーブル存在チェック、最大日付取得等）。
    - デフォルトのバックフィル日数・カレンダー先読み等の定数を設定。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar による営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB 登録値優先、未登録日は曜日ベース（週末）フォールバックの一貫した挙動を採用。
    - 安全性制限: 探索は _MAX_SEARCH_DAYS（デフォルト 60 日）以内に制限し無限ループを防ぐ。
    - calendar_update_job(conn, lookahead_days=90): J-Quants クライアント経由で差分取得・バックフィルを行い market_calendar を更新。取得・保存に失敗した場合は 0 を返す。
    - jquants_client 経由の取得・保存で例外捕捉・ログ出力。

- リサーチ機能 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum ファクター: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA に対する乖離）を計算する calc_momentum。
    - Volatility / Liquidity ファクター: 20 日 ATR（atr_20/atr_pct）、avg_turnover、volume_ratio を計算する calc_volatility。
    - Value ファクター: raw_financials から最新財務データを取得して PER / ROE を計算する calc_value。
    - DuckDB の SQL ウィンドウ関数を活用して効率的に集計。データ不足時は None を返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関による評価、サンプル数不足時は None。
    - ランク関数: rank(values) — 同順位は平均ランク（丸めで ties 検出安定化）。
    - ファクター統計サマリー: factor_summary(records, columns) — count/mean/std/min/max/median を計算。
    - pandas 等に依存せず標準ライブラリと duckdb を使用する実装。

Other
- DuckDB を主要なローカル分析 DB として利用。各モジュールは DuckDB 接続を引数で受け取り SQL と Python で処理する設計。
- OpenAI SDK（OpenAI クライアント）を使用：モデル gpt-4o-mini、JSON mode（response_format={"type": "json_object"}）想定。
- テスト容易化のため、OpenAI 呼び出し関数はモジュールごとに独立（news_nlp._call_openai_api, regime_detector._call_openai_api）しておりモック可能。
- ルックアヘッドバイアス対策: datetime.today()/date.today() をスコアリング・計算ロジック内で直接参照しない方針を明記（すべて target_date ベースで処理）。
- ロギングを各モジュールで適宜行い、API 失敗やパースエラー時に警告ログを出す設計（例外を上げずにフォールバックする箇所あり）。

Notes / 必要な事前条件
- DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が前提。これらのテーブル定義は別途用意する必要あり。
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要あり。未設定だと ValueError を発生させる。
- J-Quants クライアント（kabusys.data.jquants_client）が存在し、fetch/save 関数を提供することが前提（calendar_update_job / ETL 側で利用）。

Fixed
- （初版のため該当なし）

Changed
- （初版のため該当なし）

Security
- 環境変数の読み込みは protected set（OS 環境変数キー）を用いて .env.local/.env による OS 環境変数上書きを制御する安全機構を実装。

今後の改善候補（備考）
- ai モジュールのレスポンス検証やプロンプトの堅牢性向上、テストカバレッジ拡充。
- DuckDB バージョン差分への互換性テスト（executemany の挙動等）。
- OpenAI レート制限周りの運用ガイドラインやコスト管理。

--- 

この CHANGELOG は、提供されたコードベースの実装とドキュメント文字列から推測して作成しています。実際のリリースノート作成時は、追加の変更履歴やマイグレーション手順、既知の問題点を適宜追記してください。