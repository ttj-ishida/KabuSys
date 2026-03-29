Keep a Changelog
=================

すべての注目すべき変更はこのファイルで管理します。  
形式は "Keep a Changelog" の慣習に従います。

フォーマット
-----------
- ヘッダはリリースバージョン（[Unreleased] または [vX.Y.Z] YYYY-MM-DD）
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を基本とします。

Unreleased
----------
（次回リリースに向けた項目をここに追記してください）

[0.1.0] - 2026-03-29
-------------------
初回公開リリース。以下の主要機能・モジュールを追加しました。

Added
-----
- パッケージ基盤
  - kabusys パッケージ初期化。__version__ = "0.1.0" を定義し、公開サブパッケージ一覧を __all__ で宣言（data, research, ai, monitoring, strategy, execution などの想定）。
- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - export KEY=val 形式やクォート／エスケープ、インラインコメントを考慮した .env パーサを実装。
  - 必須環境変数取得用 _require と Settings クラスを提供。J-Quants / kabuAPI / Slack / DB パス / 環境（development, paper_trading, live）/ ログレベルの取得を実装。
  - 環境値の妥当性検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利な is_live/is_paper/is_dev プロパティを提供。
- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini + JSON mode）へバッチ送信して銘柄別センチメント（ai_score）を算出。
  - タイムウィンドウロジック（JST 基準: 前日 15:00 ～ 当日 08:30）を calc_news_window で提供。
  - バッチサイズ、1銘柄あたりの最大記事数／文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列検証、コード正規化、スコア数値化、クリッピング）を実装。スコアは ±1.0 にクリップ。
  - 書き込みは冪等性に配慮（成功したコードのみ DELETE→INSERT）。DuckDB の executemany 空リスト制約への対処あり。
  - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、日次で market_regime テーブルへ書き込む score_regime を実装。
  - マクロキーワードで raw_news をフィルタしてタイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を算出。記事がない場合や API 失敗時は 0.0 をフォールバック。
  - API のエラー区分（RateLimit, 接続, タイムアウト, APIError の status_code に基づく再試行）に対するリトライ処理を実装。
  - レジームスコアはクリップされ、閾値に応じて "bull"/"neutral"/"bear" を付与。DB への書き込みはトランザクションで冪等に実行（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK を試行）。
  - news_nlp の内部実装と結合しない設計（各モジュールが独自に _call_openai_api を持つ）。
- データ処理（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar）を実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータがない日については曜日ベース（土日除外）でのフォールバックを採用し、DB 登録値が存在する場合は優先する一貫性のある挙動を実現。
    - calendar_update_job により J-Quants クライアント経由で差分取得・バックフィル・健全性チェック（極端に未来の last_date の検出）を行い、DB に冪等的に保存する。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。ETL 実行の集計・品質問題・エラー概要を保持し、辞書化を提供。
    - 差分取得ロジック、バックフィル、品質チェックを想定した設計。_get_max_date 等のユーティリティを実装。
- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）などのファクター計算関数を実装（DuckDB の SQL とウィンドウ関数を活用）。
    - 関数は prices_daily / raw_financials のみ参照し、ルックアヘッドを防ぐ設計。結果を (date, code) をキーとする dict リストで返す。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 非依存で標準ライブラリと DuckDB のみで完遂する設計。
- テスト・運用面の配慮
  - どのモジュールも datetime.today()/date.today() を内部ロジックで直接参照しない（ルックアヘッドバイアス対策）。target_date を明示的に渡す設計。
  - OpenAI 呼び出し箇所はテスト時に差し替えられるよう実装（unittest.mock.patch での置換を想定）。
  - API 失敗時はフェイルセーフで継続（多くのケースでスコアを 0.0 にフォールバックまたは該当コードをスキップ）。
  - DuckDB を前提にした実装（日付変換ユーティリティ等を含む）。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし。

Deprecated
----------
- 初回リリースのため該当なし。

Removed
-------
- 初回リリースのため該当なし。

Security
--------
- 初回リリースのため該当なし。ただし以下は注意事項として明記:
  - OpenAI API キーやその他機密情報は Settings 経由で環境変数から取得する想定。.env ファイルの取り扱いに注意してください。
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや CI で利用）。

補足メモ
--------
- このリリースはライブラリ内部の多くの DB テーブル（prices_daily, raw_news, raw_financials, market_regime, ai_scores, market_calendar, news_symbols 等）を前提としています。実行前にスキーマ/初期データの準備が必要です。
- 外部依存: duckdb, openai SDK。J-Quants や kabuステーション向けクライアント（kabusys.data.jquants_client など）は参照されていますが、この CHANGELOG は現行コードベースが提供する機能に基づいて記述しています。

---- 
作成: kabusys v0.1.0 のコードベースから推測して CHANGELOG を作成しました。必要ならば日付の調整や各項目の詳細化（例: 関数シグネチャや定数値の明記）を行います。