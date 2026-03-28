# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-28

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - パブリックモジュール群を公開 (data, strategy, execution, monitoring)。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須キーをプロパティとして公開。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供（expanduser対応）。
    - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL 検証を実装。
    - is_live / is_paper / is_dev の簡易判定プロパティを追加。

- AI（ニュースNLP、レジーム判定） (src/kabusys/ai/*.py)
  - ニュースセンチメント解析モジュールを実装（news_nlp.score_news）。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で処理）。
    - raw_news と news_symbols を銘柄別に集約し、最大記事数・最大文字数でトリム。
    - 銘柄を最大 20 コードずつバッチで OpenAI（gpt-4o-mini、JSON mode）へ送信。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）と指数バックオフを実装。
    - レスポンス検証（JSON 抽出、results リスト、code/score 検証）、スコアを ±1.0 にクリップ。
    - 成功分のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、トランザクション制御）。
    - テスト用に _call_openai_api をパッチ可能な設計。
  - 市場レジーム判定モジュールを実装（regime_detector.score_regime）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して daily レジームを判定（bull / neutral / bear）。
    - calc_news_window を利用してニュースウィンドウを算出、raw_news からマクロキーワードでフィルタ。
    - OpenAI（gpt-4o-mini、JSON mode）でマクロセンチメントを取得、同様にリトライ/フォールバック実装。
    - レジームスコア算出と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 失敗時は macro_sentiment=0.0（中立）で継続するフェイルセーフ。

- 研究（Research）機能 (src/kabusys/research/*.py)
  - ファクター計算（factor_research）
    - モメンタム: 約1/3/6ヶ月リターン、200日移動平均乖離（ma200_dev）。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - バリュー: EPS/ROE から PER/ROE を算出（raw_financials と prices_daily を参照）。
    - DuckDB を用いた SQL ベース実装で、結果は (date, code) キーの辞書リストで返却。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定 horizon（デフォルト [1,5,21]）のリターンを一度のクエリで取得。
    - IC 計算（calc_ic）: スピアマンランク相関（ランクは平均順位、ties 対応）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）。
    - 外部依存を極力避けた（標準ライブラリのみ）実装。

- データ基盤（Data） (src/kabusys/data/*.py)
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルの参照／更新ロジックおよび営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索日数制限（_MAX_SEARCH_DAYS）を導入。
    - calendar_update_job: J-Quants API からの差分取得、バックフィル（直近 _BACKFILL_DAYS 日）と健全性チェックを実装。
  - ETL パイプライン基盤（pipeline, etl）
    - ETLResult データクラスを追加。ETL 実行結果の集約（取得数、保存数、品質問題、エラー一覧）を提供。
    - パイプラインユーティリティ: テーブル最大日付取得、テーブル存在チェックなど。

- モジュール再エクスポート
  - data.etl から ETLResult を再エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意点 / 動作上の挙動
- OpenAI API
  - OpenAI クライアント（OpenAI(api_key=...)）を直接使用。環境変数 OPENAI_API_KEY を期待。api_key 引数で明示的に注入可能。
  - API レスポンスは JSON mode を期待し、JSON パースに失敗するケースは復元ロジック（最外の {} 抜き出しなど）で対処。
  - リトライ後も失敗した場合は該当銘柄やマクロセンチメントを 0.0（中立）扱いで処理継続し、例外を投げずにフェイルセーフを提供する設計。
- データベース
  - DuckDB を前提。各種書き込みはトランザクションで冪等に行う（DELETE → INSERT）。
  - DuckDB の executemany に空リストを渡せないバージョンに配慮して空チェックを行っている。
- 設定
  - 必須環境変数が未設定の場合は早期に ValueError を送出する（Settings の各プロパティ、score_news/score_regime の api_key 解決）。
  - .env の自動ロードはプロジェクトルートが見つからない場合はスキップされる。

### テスト性 / 拡張性
- OpenAI 呼び出し部分は内部関数（_call_openai_api）で分離しており、unittest.mock.patch による差し替えでテスト可能。
- レスポンス検証・切り捨て・部分書き込み（code を絞る）等により、部分失敗に強い設計。
- 日付操作はすべて target_date ベースで行い、datetime.today()/date.today() の参照を避けてルックアヘッドバイアスを低減。

### 既知の制限 / 今後の改善候補
- 現バージョンでは PBR・配当利回りなどのバリューファクターは未実装。
- news_nlp の出力フォーマットが LLM に依存するため、将来的に冗長な前後テキストへの耐性やスコア合成戦略の改善を検討。
- calendar_update_job や ETL の外部 API 呼び出しは例外ハンドリングを行うが、リトライ戦略や監視・アラートの強化が望ましい。

---

このリリースに関する問い合わせやバグ報告は issue を作成してください。