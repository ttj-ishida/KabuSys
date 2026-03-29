KEEP A CHANGELOG
=================

すべての重要な変更をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠しています。
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報
    - src/kabusys/__init__.py: パッケージ名・バージョン宣言（__version__ = "0.1.0"）と公開サブパッケージ定義（data, research, ai, …）。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env パーサの実装：コメント・export 形式・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント処理に対応。
    - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - 環境変数取得ラッパ（Settings クラス）を提供。必須変数取得時は未設定で ValueError を送出。
    - 主要設定プロパティ群（J-Quants / kabu ステーション / Slack / DBパス / 実行環境 / ログレベル判定 等）。
    - KABUSYS_ENV と LOG_LEVEL の許容値検証。

- データプラットフォーム（Data）
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理機能。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - カレンダーデータがない場合の曜日ベースフォールバック（週末は休場扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装。
    - DuckDB に対する堅牢な日付変換・テーブル存在チェックや最大探索日数制限を実装。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの骨格（差分取得、バックフィル、品質チェックとの連携）。
    - ETLResult データクラス（target_date, fetched/saved カウント、品質問題・エラーの集約、シリアライズ用 to_dict）。
    - DuckDB を前提としたテーブル存在／最大日付取得ユーティリティを実装。
    - idempotent な保存（DELETE → INSERT など）とトランザクション処理（BEGIN/COMMIT/ROLLBACK）を考慮。

- AI モジュール（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄別に集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能。
    - ニュースウィンドウ計算（JST基準の前日15:00～当日08:30 を UTC naive datetime に変換）。
    - バッチ処理（最大 20 銘柄／チャンク）、トークン肥大化対策（記事数・文字数上限）。
    - JSON Mode を利用した出力期待とレスポンスの厳密なバリデーション（results 配列、code/score の検査）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。致命的エラーは個チャンクをスキップして処理継続（フェイルセーフ）。
    - テスト向けフック: _call_openai_api を patch して差し替え可能。

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定ロジック（bull / neutral / bear）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で判定。
    - マクロニュース抽出用キーワードリスト、OpenAI 呼び出しの独立実装、API エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止: datetime.today()/date.today() を利用せず、DB クエリは target_date 未満のデータのみ参照。

- リサーチ・ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value, Liquidity 等のファクター計算関数を提供:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
      - calc_volatility: 20 日 ATR, ATR の相対値、20 日平均売買代金、出来高比率等。
      - calc_value: raw_financials から最新財務を取得し PER / ROE を計算。
    - DuckDB による SQL ベースの計算（prices_daily / raw_financials のみ参照）。データ不足時は None を返す設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman の ρ をランクで算出）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等に依存せず標準ライブラリのみで実装。ルックアヘッドバイアス対策のため target_date に依存する設計。

- 共通・ユーティリティ
  - DuckDB を主要な永続化レイヤーとして使用。全モジュールでトランザクション処理・空チェック・互換性考慮（DuckDB 0.10 の executemany の制約など）を組み込んだ実装。
  - ロギング、警告出力、例外発生時のロールバック保証（ROLLBACK 失敗時の警告ログ）を全体で徹底。
  - テストしやすさを考慮した設計（API 呼び出しの差し替えポイント、明示的な入力引数での API キー注入など）。
  - 全体的に「失敗しても例外を投げず継続する」設計方針（フェイルセーフ）を採用した箇所が多い（AI API 呼び出し失敗時のフォールバック、データ不足時の中立値等）。

Security
- 環境変数からの機密情報取得は Settings を通じて行う。自動 .env ロード時に OS 環境変数を保護する仕組みを実装（.env の override 制御と protected set）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Required environment variables
- 以下は少なくとも設定が想定される環境変数の例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI 機能を使用する場合）
  - DUCKDB_PATH, SQLITE_PATH（データベースパス）
  - KABUSYS_ENV（development | paper_trading | live）
  - LOG_LEVEL（DEBUG | INFO | WARNING | ERROR | CRITICAL）
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements
- 本リリースは DuckDB と OpenAI（gpt-4o-mini）を利用したデータ処理・AI評価パイプラインの初期版を含みます。今後、API の仕様変更・モデル選択・性能改善に合わせて機能追加・改善を予定しています。