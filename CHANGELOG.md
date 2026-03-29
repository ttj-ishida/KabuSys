Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての変更はセマンティックバージョニングに従います。  
このファイルはコードベースから推測した機能追加・設計方針・重要な挙動をまとめたものです。

Unreleased
---------
- （現在未実装／未リリースの変更はここに記載します）

0.1.0 - 2026-03-29
-----------------
Added
- パッケージ初期リリース: kabusys v0.1.0 を公開
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を定義

- 設定管理（環境変数・.env 自動ロード）
  - src/kabusys/config.py
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .env ファイルのパースは export 形式、クォート、エスケープ、インラインコメント（スペース直前の # をコメント扱い）を考慮。
    - OS 環境変数を保護する protected キーセットを導入し、.env.local は既存 OS 変数を上書きしない設定が可能。
    - 必須環境変数取得用 _require 関数と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - デフォルト値やバリデーション:
      - KABUSYS_ENV (development|paper_trading|live)
      - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
      - データベースパスのデフォルト（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）

- AI（ニュースNLP / 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を使って一括センチメント評価。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）を calc_news_window で計算。
    - バッチ/トリミング:
      - 1 API 呼び出しで最大 _BATCH_SIZE=20 銘柄を処理。
      - 1銘柄あたり最大 _MAX_ARTICLES_PER_STOCK=10 記事、_MAX_CHARS_PER_STOCK=3000 文字にトリム。
    - 再試行・耐障害性:
      - 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ（最大回数 _MAX_RETRIES）。
      - API 失敗時はスキップして処理継続（フェイルセーフ）。
    - レスポンス検証:
      - JSON の抽出・バリデーションを行い、未知コードや非数値スコアを無視。
      - スコアは ±1.0 にクリップ。
    - DB 書き込み:
      - 成功したコードのみ ai_scores テーブルを置換（DELETE → INSERT）して部分失敗時の既存データ保護。
      - DuckDB の executemany の仕様に配慮し、空リストバインドを避けるチェックを実装。
    - テストのために OpenAI 呼び出しを差し替え可能（内部の _call_openai_api を patch 可能）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio 計算は target_date 未満のデータのみを使いルックアヘッドを防止。
    - マクロニュースは news_nlp.calc_news_window で決定したウィンドウからタイトルを抽出し、OpenAI（gpt-4o-mini）に JSON 出力で問い合わせ。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 最終結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - OpenAI 呼び出し関数はモジュール内で独立実装し、モジュール間の結合を抑制。こちらもテストで差し替え可能。

- データプラットフォーム（ETL / カレンダー / ユーティリティ）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を提供（J-Quants API を利用して差分取得→保存）。
    - market_calendar がない場合のフォールバック（曜日ベース: 土日を休場扱い）。
    - next_trading_day / prev_trading_day / is_trading_day / is_sq_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - 安全策:
      - 最大探索日数制限 _MAX_SEARCH_DAYS（無限ループ防止）
      - バックフィル _BACKFILL_DAYS と先読み _CALENDAR_LOOKAHEAD_DAYS
      - last_date が過度に未来の場合の健全性チェック（_SANITY_MAX_FUTURE_DAYS）
    - DB に NULL が混在するケースや未登録日の扱いに関するログ出力やフォールバックの一貫性を確保。

  - src/kabusys/data/pipeline.py / etl.py
    - ETL パイプラインの枠組みを実装（差分取得、idempotent 保存、品質チェック連携）。
    - ETLResult データクラスを提供（target_date, fetched/saved counts, quality_issues, errors を含む）。
    - 保存および品質チェックの設計:
      - backfill_days デフォルトあり（後出し修正を吸収）
      - 品質チェックは致命度情報を保持しつつ処理を継続（呼び出し元の判断に委ねる）
      - jquants_client からの保存関数を利用
    - データベース存在確認・最大日付計算などのユーティリティ実装。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム (calc_momentum)、ボラティリティ/流動性 (calc_volatility)、バリュー (calc_value) を実装。
    - 戦略設計書（StrategyModel.md Section 3）に基づく指標を SQL（DuckDB）で計算する設計。
    - 各関数は prices_daily / raw_financials のみ参照し、本番口座や発注 API へのアクセスはなし。
    - 戻り値は (date, code) を含む dict のリスト形式で返却（欠損時は None を返す設計）。
    - ATR や移動平均など、必要データ不足時に None を返すロバスト設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC（スピアマンのランク相関）calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
    - rank は同順位を平均ランクで処理し、丸め誤差対策として round(v, 12) を利用。

- 共通実装方針（横断的）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接参照しない関数設計（target_date を明示的に受ける）。
  - OpenAI 呼び出しでのリトライ／バックオフ、エラー種別の分離（RateLimit, Connection, Timeout, APIError の扱い）、および JSON レスポンスパースの堅牢化を採用。
  - DuckDB を想定した SQL 実装と互換性対策（executemany の空配列回避や date 型変換ユーティリティ等）。
  - テスト容易性を考慮し、外部 API 呼び出し箇所は差し替え可能にしている（内部 _call_openai_api の patch 等）。

Changed
- 初回リリースのため該当無し

Fixed
- 初回リリースのため該当無し

Notes / 備考
- OpenAI API の利用に関する設定は環境変数 OPENAI_API_KEY を参照する（関数引数で注入可能）。
- 実際の J-Quants / kabu API クライアント実装（jquants_client 等）は data モジュール経由で利用する想定。  
- DuckDB のテーブルスキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols, market_regime 等）が事前に存在する前提の実装が多く含まれるため、実運用前にスキーマ整備が必要。

--- 
（この CHANGELOG はリポジトリ内のソースコードを元に推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース担当者による確認を行ってください。）