# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  

最新更新日: 2026-03-31

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期化とバージョン設定（__version__ = 0.1.0）。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサーは以下に対応:
    - 空行／コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しの場合、インラインコメント判定（直前が空白/タブの # をコメントと扱う）
  - .env のロード時に OS 環境変数を保護する protected 機能（.env.local は override=True で上書き可能）。
  - Settings クラスによる設定取得ユーティリティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須として明示的に取得（未設定時は ValueError）。
    - KABU_API_BASE_URL のデフォルト、データベースパス（DUCKDB_PATH / SQLITE_PATH）のデフォルトを定義。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - is_live / is_paper / is_dev のプロパティ。

- AI 関連（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて、銘柄ごとに記事を集約して OpenAI (gpt-4o-mini) に送信しセンチメント（-1.0〜1.0）を ai_scores テーブルへ保存。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - 1チャンクあたり最大 _BATCH_SIZE（20）銘柄、1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - API 呼び出しは JSON mode を使用。レスポンスのバリデーション/パース処理を実装（前後に余計なテキストが混入した場合は最外の {} を抽出して復元を試みる）。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ）。失敗時は当該チャンクをスキップし他の処理を継続（フォールセーフ）。
    - スコアは ±1.0 にクリップ。書き込みは部分失敗を避けるため対象コードのみ削除→挿入の冪等更新。
    - テスト容易性のため _call_openai_api をパッチで差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを取得。API 失敗時は macro_sentiment を 0.0 として続行。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト用に OpenAI 呼び出し箇所を差し替え可能。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離率）。
    - ボラティリティ・流動性: atr_20（20日ATR平均）, atr_pct, avg_turnover, volume_ratio。
    - バリュー: per（EPS が 0 または欠損時は None）, roe（raw_financials から取得）。
    - DuckDB 上の SQL を主体とした実装。結果は (date, code) キーの辞書リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）に対応、horizons の入力検証。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関（ランクは同順位の平均ランクを使用）。
    - rank / factor_summary：ランク化ユーティリティと、count/mean/std/min/max/median を計算する統計サマリー関数。
    - 外部依存（pandas 等）を使わない実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - カレンダー未取得時は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得→冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を呼ぶ）。
    - lookahead / backfill / 健全性チェック（未来日が過剰な場合はスキップ）等の設計を実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分取得・保存・品質チェックのための ETLResult データクラスを公開。
    - _get_max_date / _table_exists 等のユーティリティを用意。
    - J-Quants クライアント（jquants_client）との連携を想定し、保存処理は冪等に行う設計。
    - 品質チェックは問題を収集して ETLResult に格納（呼び出し側で対処、Fail-Fast ではない）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の読み込みで OS 環境変数を保護する仕組み（protected set）を採用。これによりシステム環境変数が意図せず .env によって上書きされることを防止。

### Notes / Design Decisions
- ルックアヘッドバイアス対策:
  - AI / ニュース / レジーム / ETL / リサーチ系の関数は内部で datetime.today() や date.today() を参照せず、target_date 引数を明示的に受け取る設計。
  - DB クエリでも date < target_date や半開区間等を用いてルックアヘッドを防止。
- DuckDB 互換性:
  - executemany に空リストを渡さないチェックなど、DuckDB バージョン差異への耐性を実装。
- OpenAI 呼び出し関連:
  - JSON mode を期待する実装だが、レスポンスに余計なテキストが混入する可能性を考慮したパース回復ロジックや、各種例外に対するリトライ/フォールバックを実装。
  - テストのために _call_openai_api をパッチ差し替え可能にしている箇所が複数ある。

---

この CHANGELOG はコードから推測できる機能・設計方針・フェイルセーフ・インターフェースに基づいて作成しています。実際のリリースノートや変更履歴とは差異がある場合があります。必要であれば対象部分ごとに詳細な説明や例（使用例・API サンプル）を追加できます。