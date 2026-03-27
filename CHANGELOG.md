# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27

Added
- パッケージ初期リリース。
- パッケージメタ情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - モジュール群を公開: data, strategy, execution, monitoring。
- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを提供。
  - .env ファイル自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - .env 行パーサは `export KEY=val`、クォート（'"/""）、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 必須設定を取得する _require 関数と Slack / J-Quants / kabu API / DB パスなどのプロパティを備えた Settings（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
  - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値チェック）と便利な is_live/is_paper/is_dev プロパティ。
- AI（自然言語処理）関連（src/kabusys/ai）
  - ニュースのセンチメントスコアリング: score_news（news_nlp モジュール）
    - J-Quants の raw_news / news_symbols / ai_scores を利用して、指定時間ウィンドウの記事を銘柄別に集約。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄/コール）、JSON Mode を期待してレスポンスを検証・抽出。
    - チャンク処理、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証ロジック（results リスト、code/score の妥当性、スコアの ±1.0 クリップ）。
    - DuckDB への冪等書き込み（対象コードのみ削除 → 挿入。空パラメータを避けるための executemany ガード）。
    - テスト容易性のため _call_openai_api をパッチ可能。
  - 市場レジーム判定: score_regime（regime_detector モジュール）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、ma200 比率計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成、冪等 DB 書き込みを実行。
    - API 失敗時フェイルセーフ（macro_sentiment = 0.0）、ma200 計算に必要データ不足時は中立（1.0）として扱う。
    - OpenAI クライアントは明示的に OpenAI(api_key=...) を生成しリトライ処理を実装。
- データ関連（src/kabusys/data）
  - ETL 結果を表すデータクラス ETLResult とその再エクスポート（data.pipeline.ETLResult を data.etl で公開）。
  - ETL パイプライン基盤（pipeline モジュール）
    - 差分更新、backfill、品質チェック（quality モジュールとの連携）を想定した設計。
    - DuckDB を用いた最大日付取得ユーティリティ等を提供。
  - マーケットカレンダー管理（calendar_management モジュール）
    - market_calendar を参照して営業日判定、次/前営業日取得、期間内営業日リスト取得（DB 値優先、未登録日は曜日ベースでフォールバック）。
    - JPX カレンダー差分取得・保存を行う calendar_update_job（J-Quants クライアント経由）。バックフィル・健全性チェックを実装。
    - is_sq_day / is_trading_day / next_trading_day / prev_trading_day / get_trading_days といったユーティリティを提供。
- リサーチ（src/kabusys/research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離等の計算（prices_daily の SQL 窓関数利用）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE の算出（report_date <= target_date の最新レコードを採用）。
    - 設計として外部 API に依存せず DuckDB のみ参照、結果は (date, code) をキーとする dict リストで返却。
  - feature_exploration モジュール
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
    - rank / factor_summary: ランク化（同位平均ランク処理）と基本統計量集計（count/mean/std/min/max/median）を提供。
- ユーティリティ設計の特徴（横断的）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() をスコア計算内部で直接参照しない設計（target_date を明示的に渡す）。
  - DuckDB を主な永続化層として想定した SQL/Python 混合実装。
  - API 呼び出しのフォールバック戦略（失敗時に例外を投げずにスキップ・デフォルト値で継続）を多くの箇所で採用。
  - テスト容易性のためのパッチポイント（例: _call_openai_api の差し替え）を用意。

Changed
- （初版のためなし）

Fixed
- （初版のためなし）

Deprecated
- （初版のためなし）

Removed
- （初版のためなし）

Security
- OpenAI API キーは明示的に引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を参照。キー未設定時に ValueError を返すことで誤った呼び出しを防止。

Notes / Implementation details
- OpenAI 呼び出しでは gpt-4o-mini と JSON Mode（response_format={"type": "json_object"}）を使用する想定。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 相当の扱い）している。
- news_nlp と regime_detector は互いに内部の _call_openai_api 実装を共有せず、モジュール間結合を低く保つ設計。
- DuckDB バインドの互換性（executemany に空リストを渡せない件等）を考慮した実装の防御的コーディングが行われている。

お問い合わせ
- バグ報告や改善提案は issue を立ててください。