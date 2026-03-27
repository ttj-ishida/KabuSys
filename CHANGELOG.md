# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
現在のリリースはパッケージ内のソースコードから推測して作成した初回公開相当の内容です（バージョン: 0.1.0）。  
日付は 2026-03-27。

## [Unreleased]
- 今後の変更予定を記載します。

## [0.1.0] - 2026-03-27

### Added
- パッケージの初期公開
  - パッケージ名: kabusys、__version__ = 0.1.0
  - エントリポイントとして `kabusys` パッケージとサブパッケージ（data, research, ai, monitoring, strategy, execution 等想定）の公開設定を追加。

- 環境設定管理 (kabusys.config)
  - .env / .env.local を自動的にプロジェクトルートから読み込む機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に __file__ から探索（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いなどに対応）。
  - 環境変数取得ラッパー Settings を導入し、必須キー取得時のチェックを提供。
  - 主要設定項目をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL 検証）
    - is_live / is_paper / is_dev の便宜プロパティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを算出・ai_scores テーブルへ書き込み。
  - 主な実装仕様:
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換して DB と比較）
    - 1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - バッチ処理: 最大 20 銘柄単位で API コール（_BATCH_SIZE）
    - 再試行: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ（最大回数実装）
    - レスポンスバリデーション（results 配列・code/score 検査）とスコアの ±1.0 クリップ
    - 部分失敗時の安全性: 書き込みは対象コードのみ DELETE → INSERT（既存スコア保護）
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で market_regime テーブルへ書き込み。
  - 主な実装仕様:
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッドバイアス対策）
    - マクロ記事はキーワードフィルタで抽出（_MACRO_KEYWORDS）し最大件数制限
    - OpenAI 呼び出しは gpt-4o-mini、JSON レスポンスを期待。APIエラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）
    - 冪等な DB 書き込み (BEGIN / DELETE / INSERT / COMMIT) を実行
    - レジームは regime_score を閾値で判定して "bull"/"neutral"/"bear" を付与

- データプラットフォーム関連（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを定義し、取得件数・保存件数・品質問題・エラー概要を集約。
    - 差分更新・バックフィル・品質チェックの設計方針を反映。
  - calendar_management モジュール
    - market_calendar テーブルの管理、JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由でデータ取得・保存。
    - 営業日判定ユーティリティを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB にカレンダーがない場合は曜日ベースでフォールバック（週末は非営業日）。不整合や NULL 値はログ出力で通知。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）やバックフィル・健全性チェックを実装。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、200日移動平均乖離、20日 ATR、平均売買代金、出来高比率、PER/ROE 等を DuckDB と SQL で計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - 計算は prices_daily / raw_financials のみ参照し、ルックアヘッド回避のため target_date に対する取り扱いを厳密に実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - Pandas 等の外部依存を使わず標準ライブラリで実装。

- 低レベルユーティリティ
  - DuckDB 接続を前提にした各種テーブルチェックや日付変換ユーティリティを実装（_table_exists / _get_max_date など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取扱い
  - 関数は api_key を引数で受け取れる。None の場合は環境変数 OPENAI_API_KEY を参照。
  - API キー未設定時は ValueError を送出して明示的に失敗する（安全性のため）。

## 注意事項（実装上の重要な挙動・前提）
- 期待する DuckDB テーブル:
  - prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime など。
- 時刻・日付の取扱い:
  - ルックアヘッドバイアス防止のため、主要関数は datetime.today() / date.today() を内部で参照しない（target_date を明示する設計）。
  - ニュース時間ウィンドウは JST 基準から UTC に変換して DB と比較する。
- OpenAI 呼び出し:
  - gpt-4o-mini を前提。JSON Mode を利用して厳密な JSON を期待するが、復元処理（前後の余計なテキストから {} を抽出）も実装。
  - 再試行とバックオフが組み込まれており、API/ネットワーク障害時はフェイルセーフで継続（スコアは 0.0 または該当銘柄をスキップ）。
- .env パーサの振る舞い:
  - export を先頭につけた定義、クォート内のバックスラッシュエスケープ、コメント（#）の扱いなどを想定しているため、一般的な .env フォーマットに対応。
  - OS 環境変数は .env の自動読み込みで上書きされない（.env.local は override=True だが protected set により OS 環境は保護）。
- 部分失敗時の DB 保護:
  - ai_scores / market_regime などの書き込みは部分的な DELETE→INSERT を行うことで、他データの消失を防ぐ設計になっている。

この CHANGELOG はソースコードの内容から仕様や設計意図を推測して作成したものです。実際のリリースノートとして使用する際は、実装や API の変更点に応じて適宜更新してください。