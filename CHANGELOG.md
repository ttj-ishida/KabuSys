CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このリポジトリはセマンティックバージョニングを採用しています。

[Unreleased]
-------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開 API: kabusys.__init__ で data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサを実装:
    - export 形式、クォート付き値（エスケープ対応）、インラインコメントの扱い等に対応。
    - override / protected オプションで OS 環境変数を保護する読み込みが可能。
  - Settings クラスを提供し、環境変数のアクセスとバリデーションを容易に:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須値の取得。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH のデフォルト値と Path 変換。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証。
    - is_live/is_paper/is_dev の便宜プロパティ。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成。
    - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を実装（calc_news_window）。
    - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
    - 1回の API 呼び出しで最大 20 銘柄をバッチ処理（_BATCH_SIZE）。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、レスポンスを厳密にバリデート。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライ実装。
    - レスポンスのパース・検証に失敗した銘柄はスキップし、部分成功時は既存スコアを保護して ai_scores テーブルを置換（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し関数はパッチ差し替え可能（_call_openai_api をモック可能）。
    - score_news(conn, target_date, api_key=None) を公開。API キーは引数または OPENAI_API_KEY 環境変数から解決。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタで raw_news のタイトルを抽出し、OpenAI（gpt-4o-mini）により macro_sentiment を取得。
    - API 障害時は macro_sentiment を 0.0 にしてフェイルセーフ継続。
    - レジームスコアをクリップし、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開。API キーは引数または OPENAI_API_KEY 環境変数から解決。

- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar に基づく営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - calendar データが未取得の場合は曜日ベースのフォールバック（週末＝非営業日）を使用。
    - カレンダーデータの夜間更新ジョブ calendar_update_job を実装（J-Quants API 経由、バックフィル・健全性チェック含む）。
    - 最大探索日数および各種バックフィル/先読み設定を定義して安全性を確保。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - 差分更新、バックフィル、品質チェックフローの基盤を実装。
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題リスト・エラーリスト等を保持）。
    - DuckDB 上の最大日付取得やテーブル存在確認などのユーティリティ関数を実装。
    - J-Quants クライアント（jquants_client）と quality モジュールを使用する設計（各所で jq モジュールを参照）。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等を計算（不足時は None）。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠落時は None）。
    - DuckDB ベースの SQL 実行により集計を実行。外部 API にはアクセスしない。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効レコードが 3 未満の場合は None）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出。
    - rank: ties を平均ランクで扱うランク付け実装。
  - zscore_normalize を kabusys.data.stats から再エクスポート。

- 共通の設計・運用上の配慮
  - ルックアヘッドバイアス防止: 各モジュールは datetime.today() / date.today() を安易に参照せず、target_date を明示的に受け取る設計。
  - DuckDB を主要な分析 DB として利用。トランザクション制御（BEGIN/COMMIT/ROLLBACK）や executemany の空パラメータ回避など DuckDB の互換性考慮あり。
  - OpenAI API 呼び出しは失敗時のフェイルセーフ（スコア 0 / スキップ）やリトライを実装し、過剰な例外伝播を抑制。
  - テスト容易性: OpenAI 呼び出し等を patch 可能にしてユニットテストを容易に。

Notes / Requirements
- OpenAI API を利用する機能（score_news / score_regime）を使用するには OPENAI_API_KEY が必要（または各関数の api_key 引数で指定）。
- J-Quants 関連の ETL / カレンダー同期には JQUANTS_REFRESH_TOKEN 等の環境変数が必要。
- DuckDB スキーマ（prices_daily, raw_news, market_regime, ai_scores, raw_financials, news_symbols, market_calendar 等）を前提としているため、テーブル定義に合わせた初期化が必要。
- Slack 通知等を利用するには SLACK_BOT_TOKEN / SLACK_CHANNEL_ID が必須。

Fixed
- （初回リリースのため該当なし。ただし各所で故障時のフェイルセーフ挙動を明確に実装済み）

Changed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 外部 API キーは環境変数経由で注入する設計。キー管理はユーザー側で適切に行ってください。

謝辞
- 本リリースは ETL、データ管理、リサーチ、AI ベースのニューススコアリング・レジーム判定まで一連のパイプラインを対象とした初期実装です。今後、性能改善・ロバストネス強化・追加の研究用ユーティリティを順次追加していきます。