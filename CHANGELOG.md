CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

Added
-----
- 基本パッケージ初期実装
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パッケージ公開用 __all__ に data, strategy, execution, monitoring を追加。

- 環境変数・設定管理（kabusys.config）
  - .env/.env.local 自動ロード機能を実装（プロジェクトルート判定は .git / pyproject.toml 基準）。
  - .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL 検証
    - is_live / is_paper / is_dev の便宜プロパティ
  - 必須環境変数未設定時は明確な ValueError を送出。

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄毎に記事を集約、OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数制限）。
    - JSON Mode を期待しレスポンスをバリデーションして ai_scores テーブルへ書き込み。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。フォールバックで処理を継続（失敗コードはスキップ）。
    - テスト用に _call_openai_api をモック可能に設計。
    - calc_news_window(target_date) を公開（JSTウィンドウ -> UTC naive datetime 返却）。
    - score_news(conn, target_date, api_key=None) を公開。成功時は書き込んだ銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して
      日次でレジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込み。
    - マクロキーワードフィルタで raw_news タイトルを抽出、OpenAI（gpt-4o-mini）で macro_sentiment を算出。
    - LLM 呼び出しは独立実装（news_nlp と結合しない）でテストしやすく設計。
    - APIエラー時は macro_sentiment=0.0（中立）として継続するフェイルセーフ実装。
    - score_regime(conn, target_date, api_key=None) を公開。成功時は 1 を返す。
  - 共通設計方針
    - OpenAI API キーは引数優先、なければ環境変数 OPENAI_API_KEY を参照。
    - モデルは gpt-4o-mini、JSON mode を利用し厳密な構造を期待。
    - レスポンスパース失敗や未知コード・不正スコアは安全に無視する実装。

- Data / ETL / カレンダー（kabusys.data）
  - ETL 基盤（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラーなど）。
    - 差分更新、バックフィル、品質チェックを前提とした設計（J-Quants クライアント経由）。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得ユーティリティを提供。
  - ETL 公開インターフェース（kabusys.data.etl）: ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定と便利関数:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 未取得時は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job(conn, lookahead_days=90) で J-Quants から差分取得し保存（バックフィル・健全性チェック含む）。
    - 最大探索日数やバックフィル、先読み日数等の定数を定義して無限ループ等を回避。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を prices_daily から計算。
      - データ不足時は None を返す挙動を明示。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（True Range の NULL 伝播に配慮）。
    - calc_value: raw_financials から最新財務を取得して PER, ROE を計算（EPS=0 等では None）。
    - すべて DuckDB SQL を主体に実装し外部 API に依存しない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（営業日ベース）。
    - calc_ic: ファクターと将来リターンの Spearman rank（IC）を計算。十分なサンプルがない場合は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ。
    - factor_summary: count, mean, std, min, max, median を計算する統計サマリー。

Other notes / 品質・安全設計
-------------------------
- ルックアヘッドバイアス回避
  - AI / リサーチ関連の多くの関数は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリでは date < target_date や date = target_date といった排他条件で未来データの参照を防止。

- フェイルセーフ設計
  - LLM 失敗時は例外を上位に投げず中立スコア（0.0）で継続するケースが多く、ETL やスコア取得が部分失敗しても他データを保護する（部分書換の採用）。
  - DuckDB executemany に対する互換性対策（空リストでの executemany を回避）を実装。

- テストしやすさ
  - OpenAI 呼び出しは専用の内部関数に切り出し（_call_openai_api）・モックしやすい実装。
  - .env 自動ロードは無効化可能でユニットテスト環境を安定させる。

Changed
-------
- 初版リリースのため該当なし。

Fixed
-----
- 初版リリースのため該当なし。

Deprecated
----------
- 初版リリースのため該当なし。

Removed
-------
- 初版リリースのため該当なし。

Security
--------
- 初版リリースのため該当なし。

必要な環境変数（代表）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリングで必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 周り
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack
- DUCKDB_PATH / SQLITE_PATH: デフォルトは data/ 以下

注記
- 本 CHANGELOG はソースコードから読み取れる機能・設計意図を基に作成しています。実際のリリースノートは追加の変更履歴や実運用での観察を反映して更新してください。