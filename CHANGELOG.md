# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の規約に従ってバージョニングしています。  

- フォーマット: https://keepachangelog.com/ja/1.0.0/  
- セマンティックバージョニングに従います。

## [Unreleased]

（現在のコードベースに基づく初期リリースを作成しました。今後の変更はここに記載します。）

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買・データプラットフォーム基盤の主要機能を実装しました。

### 追加 (Added)
- パッケージの基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 設定/環境変数管理 (`kabusys.config`)
  - .env / .env.local 自動ロード機能をプロジェクトルート（.git または pyproject.toml 参照）から実行。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装。
  - .env パーサ実装（export 形式対応、クォート/エスケープ、インラインコメントの扱い、無効行スキップ）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の定義）および is_live/is_paper/is_dev ヘルパーを提供。
- データプラットフォーム - カレンダー管理 (`kabusys.data.calendar_management`)
  - market_calendar ベースの営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB データ優先、未取得日は曜日ベースのフォールバック（週末判定）を採用。
  - calendar_update_job 実装：J-Quants から差分取得して market_calendar を冪等的に保存（バックフィルと健全性チェックを含む）。
  - DuckDB のクエリ補助関数（テーブル存在チェックや日付変換ユーティリティ）を提供。
- データプラットフォーム - ETL (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETL の結果を表すデータクラス ETLResult を実装（取得件数 / 保存件数 / 品質問題 / エラー等の集約）。
  - 差分取得・バックフィル方針、品質チェックフローの仕様に対応するための基盤を実装（jquants_client, quality モジュールと連携想定）。
  - ETLResult.to_dict により品質問題をシリアライズ可能。
  - ETLResult を外側へ再エクスポート（kabusys.data.etl）。
- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算モジュール（factor_research）を実装:
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）。
    - ボラティリティ / 流動性: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率。
    - バリュー: PER / ROE（raw_financials の最新レコードを利用）。
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials を参照）。
  - 特徴量探索（feature_exploration）を実装:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、horizons 検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関を実装）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計量要約 factor_summary（count/mean/std/min/max/median）。
  - 研究用ユーティリティ zscore_normalize を data.stats から再エクスポート（kabusys.research.__init__ でまとめて公開）。
- AI（自然言語処理）モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング（news_nlp）:
    - OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメント評価機能 score_news を実装。
    - ニュースのタイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST → UTC 変換）。
    - 1銘柄あたりの記事集約（最大記事数 / 文字数トリム）、最大バッチサイズでの API 呼び出し。
    - JSON Mode を想定した出力検証・パース（冗長テキストからの JSON 抽出処理含む）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実施し、失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - スコアの有限性チェック・±1.0 でクリップ。結果は ai_scores テーブルへ冪等的に保存（DELETE → INSERT の個別実行で部分失敗を考慮）。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321（225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM センチメント、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）による JSON 形式での macro_sentiment 抽出、エラーハンドリングとリトライロジックを含む。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
  - テスト容易性を考慮して OpenAI 呼び出し (_call_openai_api) はモジュール内で分離（テスト時に patch 可能）。
- 外部依存/設計上の注意
  - DuckDB をデータベースとして想定（DuckDB のバージョン 0.10 系の挙動を考慮した実装）。
  - OpenAI SDK（chat completions）を利用。API キーは引数で注入可能、未指定時は環境変数 OPENAI_API_KEY を参照。
  - jquants_client（kabusys.data.jquants_client）との連携ポイントを想定し、データ取得・保存はそのクライアントに委譲。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注意事項 / マイグレーションガイド（初期導入メモ）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能を利用する場合）
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env/.env.local を自動でロードします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ:
  - 本コードは prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを前提とします。ETL / DB 初期化処理でスキーマを準備してください。
- OpenAI API:
  - JSON mode を前提としたプロンプト設計とレスポンスパースを行っています。API 仕様の変化がある場合は _call_openai_api 実装の調整が必要です。
- フェイルセーフ設計:
  - AI 呼び出し失敗時はスコアに中立値（0.0）を使う、チャンク失敗はスキップするなど、プロダクションで致命的な障害を避ける設計になっています。

貢献・バグ報告・改善提案は ISSUE を通じてお願いします。