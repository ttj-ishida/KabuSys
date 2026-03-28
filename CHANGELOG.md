# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトはまだ若く、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-28

### 追加
- パッケージ初期リリース。モジュール構成を公開。
  - kabusys: 主要パッケージエントリ（__version__ = 0.1.0）。
  - サブパッケージ公開: data, research, ai, monitoring, strategy, execution（__all__ に登録）。
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD 非依存）。
  - .env パーサ実装:
    - コメント行、空行を無視
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値でのインラインコメント解釈（直前がスペースまたはタブの場合）
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能
  - protected（OS 環境変数）を考慮した上書き制御
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須チェック
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値設定
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の簡易判定プロパティ
- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄別にニュースを集約、OpenAI（gpt-4o-mini）の JSON Mode を用いて一括スコア取得
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）
    - 1銘柄あたりの記事数上限・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - バッチ処理（最大 20 銘柄/リクエスト）、レスポンスの厳密なバリデーションとスコア ±1.0 のクリップ
    - レート制限 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ、その他失敗は当該チャンクをスキップ（フェイルセーフ）
    - DuckDB executemany の仕様差分（空リスト不可）を考慮した安全な書き込み（DELETE → INSERT）
    - テスト容易性: OpenAI 呼び出し関数を patch により差し替え可能（_call_openai_api）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定
    - MA 計算は target_date 未満データのみに依存し、ルックアヘッドバイアスを排除
    - マクロニュース選別にマクロキーワードリストを使用し、最大記事数制限あり
    - OpenAI 呼び出しはリトライ処理を備え、失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト用置換ポイントあり（_call_openai_api）
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - DB 登録値優先、未登録日は曜日ベースでフォールバック（週末除外）
      - 最大探索日数上限を設定して無限ループを防止
    - 夜間バッチ更新ジョブ calendar_update_job 実装:
      - J-Quants API から差分取得し market_calendar を冪等更新
      - バックフィル（直近 _BACKFILL_DAYS を再フェッチ）と健全性チェック（将来日付の異常検出）
      - jquants_client 経由で fetch/save を実行
  - ETL / パイプライン（kabusys.data.pipeline, etl）
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー概要などを格納）
    - 差分更新ロジックの土台（最終日付チェック、backfill、品質チェックフックの設計方針を明記）
    - internal ユーティリティ: テーブル存在チェック、最大日付取得、トレーディングデイト調整等
    - kabusys.data.etl は pipeline.ETLResult を再エクスポート
- リサーチ用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB 上で SQL + Python により計算
    - データ不足時の None 処理、出力は (date, code) ベースの辞書リスト
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、horizons バリデーション）
    - IC（Information Coefficient）計算（スピアマンのランク相関）と rank ユーティリティ（同順位は平均ランク処理）
    - factor_summary による基本統計（count, mean, std, min, max, median）
  - zscore_normalize はデータモジュールからの再利用を想定（__init__ で公開）
- ロギングと設計ノート
  - 各所で詳細なログ出力を実装（INFO/DEBUG/WARNING/exception）
  - ルックアヘッドバイアス対策として datetime.today()/date.today() の非依存を明記（target_date を明示的に受け取る設計）
  - DuckDB 互換性考慮（executemany の空リスト制約など）
  - OpenAI 呼び出し周りはエラー処理とパース頑健性（余分なテキストを囲う { } の抽出等）を実装

### 変更
- （初回リリースのため過去の変更はなし）

### 修正
- （初回リリースのため過去の修正はなし）

### 破壊的変更
- なし

### セキュリティ
- なし

注記:
- OpenAI API キーが必須となる機能（news_nlp.score_news, regime_detector.score_regime）は、引数での注入か環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError を送出する挙動。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）に依存するため、利用前にスキーマ準備が必要。README / DataPlatform.md / StrategyModel.md を参照のこと（コード中に参照あり）。
- テスト容易性のため外部 API 呼び出し部分（_call_openai_api 等）を差し替え可能に設計済み。

貢献:
- 初期実装（0.1.0）の機能をまとめて公開。今後、安定化・拡張（追加ファクター、監視/モニタリング、execution 周りの実装）を予定。