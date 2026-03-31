# Keep a Changelog
すべての注目すべき変更をこのファイルに記録します。変更はセマンティックバージョニングに従って分類しています。  

フォーマットは Keep a Changelog に準拠しています。

## Unreleased
（未リリースの変更はここに記載）

## [0.1.0] - 2026-03-31
初回公開リリース。以下の主要コンポーネントを実装・公開しました。

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン: 0.1.0
  - top-level __all__ に data, strategy, execution, monitoring を公開。

- 環境設定 / ロード
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検索して決定）。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env 読み込みは優先順位 OS 環境変数 > .env.local > .env（.env.local が上書き）。
    - .env のパース機能を実装:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応
      - インラインコメント処理（クォートあり/なしでの挙動差分）
    - protected set を利用した上書き制御（OS 環境変数を保護）。
    - Settings クラスを提供し、J-Quants / kabu / Slack / DB /監視 / システム設定等のプロパティを取得可能:
      - 必須環境変数取得時に未設定なら ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
      - KABUSYS_ENV の妥当性チェック（development, paper_trading, live）。
      - LOG_LEVEL の妥当性チェック（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
      - デフォルトパス（DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db, PID_FILE_PATH= data/execution.pid）とし expanduser を適用。
      - リソース閾値のデフォルト値（CPU/MEM/DISK）を提供。

- AI モジュール（OpenAI を利用した NLP/レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、gpt-4o-mini（JSON mode）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄当たり記事数/文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を導入。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ、非リトライ対象エラーはスキップして継続する設計（フェイルセーフ）。
    - レスポンスの厳格なバリデーション機能（JSON抽出、"results" 構造、コード照合、数値性チェック、スコアクリップ）。
    - テストしやすさを意識し、OpenAI API 呼び出し箇所はモック可能（_call_openai_api を patch 可能）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする score_regime を実装。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュース抽出用キーワード群（日本・米国など）を定義し、最大記事数で制限して LLM に入力。
    - OpenAI 呼び出しは専用実装でモジュール結合を避け、再試行戦略（リトライ・バックオフ）とフェイルセーフ（失敗時に macro_sentiment=0.0）を採用。
    - 最終的なスコアはクリップされ、閾値でラベル付けして DB にトランザクションで書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム / ETL / カレンダー管理
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーを管理するユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブルの存在・値に応じた DB 優先の判定ロジックと、未登録日の曜日ベースフォールバックを採用。
    - 次/前営業日の探索で最大探索日数制限を設けて無限ループを防止。
    - 夜間バッチ calendar_update_job を実装し、J-Quants クライアントからの差分取得→保存（fetch/save）を行う。バックフィル・健全性チェックあり。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを実装（target_date, 取得/保存件数, 品質チェック問題リスト, エラー概要リスト等）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した ETL パイプライン設計。
    - jquants_client 経由の idempotent 保存を前提とした設計方針を記載。
    - etl.py で ETLResult を再エクスポート。

- Research（因子・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR）、Value（PER/ROE）等の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの実装で prices_daily / raw_financials を参照。
    - ファンクションは (date, code) ベースの辞書リストを返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - Spearman 相当（ランクの Pearson）による IC 計算、同順位の平均ランク処理、統計量の計算（count/mean/std/min/max/median）を提供。
  - src/kabusys/research/__init__.py で主要関数群と zscore_normalize を再エクスポート。

- データユーティリティ
  - src/kabusys/data/calendar_management.py, pipeline.py 等、DuckDB と互換のある SQL を使用し idempotent 操作や executemany の空リスト回避等の互換性考慮を実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- API キーや機密情報の扱いに関する基本的配慮を実装:
  - 環境変数未設定時に明示的なエラーを出す設計（誤動作の防止）。
  - .env の上書き制御機構で OS 環境変数を保護。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: ニュース集計、MA 計算、ETL、AI 評価等で datetime.today()/date.today() を直接参照しない設計を徹底（target_date を明示的に受け取る）。
- フェイルセーフ: OpenAI API や外部取得が失敗しても例外を大域的に投げず、部分的にスキップして継続する（ログ出力で失敗を記録）。
- テストしやすさ: OpenAI 呼び出しやその他外部依存ポイントはモック差替え可能に実装。
- 外部依存を最小化: research モジュール等は標準ライブラリ + DuckDB のみを前提に実装（pandas 等に依存しない）。
- DuckDB のバージョン差異（executemany に空リスト不可など）に対する互換性考慮を実装。

---

この CHANGELOG はコードベースから推測して作成しています。実運用でのリリースノート作成時には、実際のコミット／リリース内容に合わせて加筆・修正してください。