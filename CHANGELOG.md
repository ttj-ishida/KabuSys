# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

全般:
- このリポジトリは日本株自動売買システム「KabuSys」の初期リリースを示します。
- DuckDB をデータストアとして想定し、J-Quants / kabuステーション / OpenAI 等の外部サービスと連携する各種モジュールを提供します。
- 設計上の方針として、ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を参照しない）、IDEMPOTENT な DB 書き込み、外部 API の失敗をフォールバックで扱う（フェイルセーフ）ことを重視しています。

[0.1.0] - 2026-04-03
----------------------------------

Added
- パッケージ初期公開
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義

- 環境設定 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
  - .env 行パーサ実装（export 構文、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート）
  - Settings クラスを提供（プロパティ経由で各種設定を取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK 閾値（監視用）
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の検証ロジック
    - ヘルパー is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング: news_nlp.score_news
    - タイムウィンドウ（JST 前日15:00〜当日08:30）を計算する calc_news_window を提供
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数に上限）
    - OpenAI (gpt-4o-mini) を JSON Mode で呼び出し、バッチ（最大 20 銘柄/回）でセンチメントを取得
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ）
    - レスポンスの厳密バリデーション（results リスト・code/score 型チェック・スコアの ±1 クリップ）
    - 成功した銘柄のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗で既存データを保護）
  - 市場レジーム判定: regime_detector.score_regime
    - ETF 1321（Nikkei225 連動型）200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジームを判定
    - マクロニュースは raw_news をマクロキーワードでフィルタし、OpenAI により -1〜1 のスコアを取得
    - レジーム合成式、閾値によるラベル付け（bull/neutral/bear）
    - DB (market_regime) への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - OpenAI 呼び出しは内部で client.chat.completions.create を使用（テスト時に差し替え可能）

- データモジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を基に営業日判定 / 次営業日 / 前営業日 / 期間内営業日リスト / SQ日判定のユーティリティを提供
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（土日を非営業日）
    - calendar_update_job: J-Quants からの差分取得と market_calendar への冪等保存（バックフィル、健全性チェックを実装）
  - ETL パイプライン (pipeline)
    - ETLResult dataclass: ETL 実行結果の集約（取得数・保存数・品質チェック結果・エラーのリスト等）
    - _table_exists や _get_max_date 等の内部ユーティリティ（DuckDB 前提）
  - etl モジュールは ETLResult を再エクスポート

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を算出（prices_daily 参照）
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を算出
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS が 0/欠損時は None）
    - SQL + window 関数主体で実装。欠損やデータ不足時の None 扱いを明確化
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括算出
    - calc_ic: Spearman（ランク相関）による IC 計算（有効レコード3未満で None）
    - rank: 同順位は平均ランクを割り当てるランク関数（丸め対策あり）
    - factor_summary: count/mean/std/min/max/median の統計サマリーを返す（None 除外）
  - research パッケージは上記関数群を再エクスポート（便利 API）

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- （既知のセキュリティ修正はなし）
- 注意: OpenAI API キー等の機密情報は環境変数で管理する設計（.env/.env.local は自動読み込みされるが OS 環境変数を保護する仕組みあり）

重要な実装上の注意点 / 要件
- 必須環境変数
  - OPENAI_API_KEY: news_nlp.score_news / regime_detector.score_regime を実行する場合必須（関数引数で注入可）
  - JQUANTS_REFRESH_TOKEN: Settings.jquants_refresh_token で必須
  - KABU_API_PASSWORD: Settings.kabu_api_password で必須
- DuckDB のスキーマ期待（主なテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
  - 各モジュールは上記テーブルの存在・列構成を前提に SQL を発行する（欠損データは None 扱い）
- 外部 API の堅牢化
  - OpenAI 呼び出しは複数のエラー種別を識別してリトライ/フォールバックを行う（RateLimitError/APIConnectionError/APITimeoutError/APIError など）
  - API レスポンスの JSON パース失敗や型不一致はログに記録して該当チャンクをスキップする設計
- ルックアヘッドバイアス対策
  - いずれのスコア算出関数も内部で現在時刻を参照しない（target_date を明示的に渡す設計）
- .env 読み込みの挙動
  - 読み込み優先度: OS 環境変数 > .env.local > .env（.env.local は .env の上書き）
  - override 動作や protected（OS 環境変数）保護を実装

既知の制約 / 今後の改善候補
- DuckDB バインドの仕様差異（executemany に空リストが渡せない等）に合わせた実装をしているため、将来 DuckDB バージョン変更時に見直しが必要な箇所あり
- news_nlp は現状 gpt-4o-mini と JSON mode を前提としているため、OpenAI SDK 仕様変更時に適合作業が必要
- 一部の関数は外部 API（J-Quants, OpenAI）に依存するため、ユニットテストではモック注入が必要（コード中で差し替え可能な設計あり）

参考（主な公開 API）
- kabusys.config.settings: 各種環境設定をプロパティで取得
- kabusys.ai.score_news(conn, target_date, api_key=None) -> 書き込み件数
- kabusys.ai.score_regime(conn, target_date, api_key=None) -> 1（成功）
- kabusys.data.calendar_update_job(conn, lookahead_days=90) -> 保存件数
- kabusys.data.pipeline.ETLResult: ETL 実行結果のデータクラス
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank

---

この CHANGELOG はソースコードの内容から推測して記載しています。実際のリリースや変更履歴に合わせて日付や項目を調整してください。