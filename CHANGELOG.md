Changelog
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, ...）で記載しています。
- 日付はリリース日を示します。

Unreleased
----------

（今後の変更をここに記載します）

0.1.0 - 2026-03-29
------------------

Initial release — 日本株自動売買・データ基盤ライブラリの初版を公開。

Added
- パッケージ基盤
  - kabusys パッケージ公開（__version__ = 0.1.0）。
  - パッケージの公開 API（__all__）に data, strategy, execution, monitoring を含める。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の読み込み機能を追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - 自動読み込みの順序: OS 環境変数 > .env.local > .env。 KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env のパース機能を強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープの処理
    - インラインコメントの扱い（クォートあり/なしでの違いを考慮）
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（検証: development/paper_trading/live）, LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のヘルパー

- AI 系機能（kabusys.ai）
  - ニュースセンチメント集約（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む機能を実装。
    - 時間ウィンドウ計算（JST 基準: 前日 15:00 〜 当日 08:30）と UTC 変換を提供（calc_news_window）。
    - 1チャンク当たり最大銘柄数（_BATCH_SIZE=20）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しのリトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score の整合性、数値チェック）とスコアの ±1.0 クリップ。
    - DuckDB 互換性考慮: executemany に空リストを渡さないガードを実装し、部分失敗時に他銘柄データを保護するため DELETE → INSERT の置換方式を採用。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（_call_openai_api をパッチ）に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime に書き込む機能を実装。
    - マクロニュース抽出（キーワードベース）と LLM スコアリング、API リトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - レジームスコアのクリップおよび閾値判定（bull/neutral/bear）。
    - DB 書き込みは冪等処理（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - テスト差替え用に _call_openai_api を独立実装（news_nlp とは共有しない設計）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定、次/前営業日算出、期間内営業日一覧取得、SQ判定等のユーティリティを実装。
    - market_calendar 未取得時の曜日ベースのフォールバック（週末は休場扱い）。
    - カレンダー更新ジョブ（calendar_update_job）: J-Quants から差分取得・バックフィル・保存処理（健全性チェックを含む）。
    - 最大探索日数やバックフィル等の安全策を導入（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。

  - ETL パイプライン基盤（kabusys.data.pipeline / etl）
    - ETL 実行結果を表すデータクラス ETLResult を実装（品質チェック情報・エラー一覧を含む）。
    - 差分取得・保存・品質チェックのためのユーティリティ（最終取得日の取得、テーブル存在確認等）。
    - 設計上の注意点（差分取得のデフォルト単位、backfill の扱い、品質チェックは収集型で呼び出し元に委ねる等）を実装。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Value（PER, ROE）、Volatility（20日 ATR）等の計算機能を追加。
    - DuckDB のウィンドウ関数を活用した SQL 主導の実装。データ不足時の None 戻し。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、horizons パラメータ検証）
    - Spearman に基づく IC 計算（calc_ic）とランク関数（rank）
    - ファクター統計サマリー（factor_summary）
  - いずれの関数も DB の prices_daily / raw_financials のみ参照し、発注や外部 API にはアクセスしない設計。

- ロギング・ロバストネス
  - 各モジュールで詳細なログ出力を追加（info/warning/debug）。
  - API 呼び出し失敗やパース失敗時もフェイルセーフ（例: マクロスコア 0.0、スキップ継続）で処理を続行する実装。

Changed
- 初版リリースにつき該当なし（初回追加のため）。

Fixed
- 初版リリースにつき該当なし（初回追加のため）。

Security
- 環境変数の取り扱いにおいて、OS 環境変数を protected として .env による上書きを制御する仕組みを導入。

Notes / Implementation details
- OpenAI API の呼び出しは gpt-4o-mini を想定し、JSON Mode のレスポンスを厳密に検証して利用する。
- 時刻・日付の扱い:
  - 日付の計算で datetime.today() / date.today() の乱用を避け、関数呼び出し側から target_date を受け取ることでルックアヘッドバイアスを防止している。
  - ニュースウィンドウは JST 基準で定義し、DB の UTC 保存と比較するよう変換している。
- DuckDB 互換性対策:
  - executemany に空リストを渡すと失敗するバージョンに対してガードを実装。
  - list 型バインドが不安定な環境への対応として個別 DELETE を使う方式を採用。
- テスト支援:
  - OpenAI 呼び出しを差し替え可能にしてユニットテストを容易にしている（モジュール内プライベート関数を patch してモック可能）。

Known issues / TODO
- 一部のファクター（PBR・配当利回り）は現バージョンで未実装（calc_value の注釈参照）。
- strategy / execution / monitoring の具体的な発注・実行ロジックは初期公開時点では宣言的な API 露出に留まっている可能性がある（実装状況はリポジトリの他ファイル参照）。

Acknowledgements
- 本リリースはロバスト性（リトライ・フォールバック・冪等性）とテスト容易性に重点を置いて設計されています。