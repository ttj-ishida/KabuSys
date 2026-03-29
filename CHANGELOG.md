# Changelog

すべての変更は Keep a Changelog の形式に従います。  
次のヘッダは重要度別に整理しています: Added / Changed / Fixed / Removed / Security。  

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点・設計上の注意点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - public API エクスポート: data, strategy, execution, monitoring（__all__）。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供（テスト用途想定）。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメントの考慮。
    - クォートなしでのコメント扱いは直前が空白/タブの場合のみとする等、実用的なパース挙動。
  - 環境変数保護機能（OS側の既存変数を protected set として保持）を実装。
  - Settings クラスを提供（プロパティ経由で各種必須値を取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABUSYS_ENV の値検証（development / paper_trading / live のみ許可）。
    - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）を Path 型で返すユーティリティ。

- ニュースNLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - 前日 15:00 JST ～ 当日 08:30 JST（内部では UTC naive datetime に変換）を対象に raw_news を集約。
    - news_symbols と結合し、銘柄ごとに最新の記事を最大 _MAX_ARTICLES_PER_STOCK 件・文字数トリムしてプロンプトを作成。
    - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信（チャンクサイズ _BATCH_SIZE=20）。
    - エラー（429、ネットワーク断、タイムアウト、5xx）は指数バックオフでリトライ。その他は失敗時にスキップ（フェイルセーフ）。
    - レスポンスの厳密検証（JSON パース、results 配列、code と score 型検査、未知コードの無視、数値性チェック）。
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - DuckDB 互換性考慮: executemany に空リストを渡さない保護を実装。
  - calc_news_window(target_date) を公開し、ニュース集計ウィンドウを計算。

- レジーム検出（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321（日経225連動型）の過去 200 日の終値から ma200_ratio を計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - raw_news からマクロ経済キーワードでフィルタしたタイトルを取得し、LLM にて macro_sentiment を取得（gpt-4o-mini、JSON Mode）。
    - レジームスコアを合成（ma 重み 0.7、macro 重み 0.3、スケーリング・クリップ処理）し、label を bull/neutral/bear に分類。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出し失敗やパース失敗時は macro_sentiment=0.0 としてフォールバック（例外を上げず継続）。
    - OpenAI 呼び出しはモジュール独自関数で実装（モジュール結合の抑制、テスト時は差し替え可能）。

- 研究用ファクター・特徴量（kabusys.research）
  - factor_research モジュールを実装:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離（必要行数未満は None）。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率（volume_ratio）。
    - calc_value(conn, target_date): PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新レコードを結合）。
    - 各関数は DuckDB 上の SQL ウィンドウ関数を主要実装に採用し、高速・一貫性を重視。
  - feature_exploration モジュールを実装:
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（LEAD を用いて一括取得）、horizons バリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関を実装（同順位は平均ランク）。
    - rank(values): 同順位は平均ランクとして処理（丸めによる ties 対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリ。

- データ管理（kabusys.data）
  - calendar_management モジュールを実装:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得のときは曜日ベース（平日）でフォールバックする一貫したロジック。
    - 最大探索日数 _MAX_SEARCH_DAYS による安全策。
    - calendar_update_job(conn, lookahead_days): J-Quants から差分取得し market_calendar に冪等保存、バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline.py / etl.py）:
    - ETLResult dataclass を公開（pipeline.ETLResult を etl.py から再エクスポート）。
    - 差分取得ロジック、バックフィル、品質チェック（kabusys.data.quality と連携）の骨格を実装。
    - DuckDB の型変換（日付）やテーブル存在チェック等のユーティリティを提供。

- ロギング・設計上の方針
  - ルックアヘッドバイアス対策: モジュールは datetime.today()/date.today() を直接参照しない設計（一部ジョブでは外部で today を取得）。
  - フェイルセーフ: 外部 API の障害では 0.0（中立）やスキップを選び、全体処理を継続する方針。
  - DuckDB の互換性考慮（executemany の空配列扱い等）と型変換ユーティリティを整備。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）  
  - ただし設計上のバグ回避策を実装:
    - DuckDB executemany が空配列を受け取れない制約への対処（空チェックを挟む）。
    - OpenAI API の APIError で status_code が属性として存在しない可能性へ getattr による安全取得。

### Removed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーや各種トークンは Settings 経由で必須チェックを行い、未設定時は ValueError を送出して早期検出。  
- .env 自動ロードは環境変数で確実に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記:
- 本 CHANGELOG は提供されたソースコードの実装とドキュメント文字列から推測して作成しています。実際のリリース手順やドキュメント日は任意に調整してください。