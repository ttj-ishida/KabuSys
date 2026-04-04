# Changelog

すべての注目すべき変更はこのファイルに記載します。  
形式は「Keep a Changelog」に準拠します。

なお、この CHANGELOG は提供されたコードベースからの推測に基づいて作成しています（実装ファイル一覧・関数挙動・設計方針を反映）。

## [Unreleased]
特になし。

## [0.1.0] - 2026-04-04
最初のリリース。システムは日本株自動売買プラットフォームのコアユーティリティ群（設定管理、データETL/カレンダー、リサーチ用ファクター計算、AIによるニュース解析／市場レジーム判定）を提供します。

### Added
- パッケージ初期化
  - pkg: kabusys
  - バージョン定義: __version__ = "0.1.0"
  - 公開モジュール: data, strategy, execution, monitoring (__all__)

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - プロジェクトルート自動探索: .git または pyproject.toml を基準に .env 自動ロードを実装。作業ディレクトリに依存せずパッケージ配布後も動作。
  - .env パーサ実装: export 文対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理をサポート。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。既存の OS 環境変数は保護（protected set）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート（テスト用）。
  - Settings クラス: 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_TOKEN/USER_ID, DUCKDB_PATH, SQLITE_PATH, PID/KILL フラグパス、リソース閾値、環境名/ログレベル検証）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - 必須環境変数未設定時は ValueError を送出するユーティリティ _require。

- AI モジュール (src/kabusys/ai)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - ニュースのセンチメントスコアリング機能 score_news を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）に基づく記事抽出（calc_news_window）。
    - raw_news + news_symbols から銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
    - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信（1コール最大20銘柄）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ＋リトライ。
    - レスポンスバリデーション（JSON復元、results リスト・code/score 検証、数値型チェック、±1.0 でクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT を executemany で行い、部分失敗時に既存スコアを保護）。
    - APIキー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - APIエラー時は個別チャンクをスキップして処理継続（フェイルセーフ）。

  - regime_detector (src/kabusys/ai/regime_detector.py)
    - 市場レジーム（bull / neutral / bear）判定機能 score_regime を実装。
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）を計算し（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロニュースの LLM センチメントと重み付きで合成（70% MA, 30% マクロ）。
    - マクロニュース抽出はキーワードベース（複数キーワード群）でタイトルを取得し、最大記事数を制限。
    - OpenAI を用いたマクロセンチメント評価（JSON モード・リトライ）と合成スコアの閾値判定。
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK と警告）。
    - APIエラー時は macro_sentiment=0.0（フォールバック）として処理を継続。

  - ai パッケージの公開: score_news を __all__ で公開（ai.__init__）。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、および 200 日移動平均乖離 (ma200_dev) を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算（必要行数未満は None を返す）。
    - calc_value: raw_financials から最新財務データを取得して PER, ROE を計算（EPS が 0/欠損時は None）。
    - 設計上、外部API呼び出しなし、DuckDB の SQL と Python を組合せて実装。

  - feature_exploration.py
    - calc_forward_returns: target_date 以降の将来リターン（指定ホライズン）を一括クエリで計算。horizons の検証あり（正の整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効データ <3 件なら None）。
    - rank: 同順位は平均ランクを返す。浮動小数の丸めで ties 漏れを低減。
    - factor_summary: 各カラムに対する count/mean/std/min/max/median を計算（None を除外）。
  - research パッケージの公開: calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank を __all__ で公開。

- データプラットフォーム / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - 市場カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
  - DB に market_calendar があればそれを優先し、未登録日は曜日ベースのフォールバック（週末は非営業日）。
  - 最大探索範囲を設定して無限ループ回避（_MAX_SEARCH_DAYS）。
  - calendar_update_job: J-Quants（jquants_client 経由）から差分取得して market_calendar を冪等保存。バックフィル（日数指定）と健全性チェック（将来日付の異常検出）を実装。
  - DuckDB の戻り値（任意）を date に安全に変換するユーティリティ実装。

- ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラーの収集、has_errors / has_quality_errors / to_dict を備える）。
  - 差分取得・backfill・品質チェックの方針を反映した設計定数（最小データ日、カレンダー先読み、デフォルト backfill 日数等）。
  - データ保存は jquants_client の save_* 系関数を前提とした冪等保存を想定。
  - data.etl で ETLResult を再エクスポート。

- DuckDB 関連の互換性配慮
  - executemany に空リストを渡せない（DuckDB 0.10 の制約）点へ対応するガードを実装。
  - SQL クエリはルックアヘッドバイアスを避けるため date 比較を厳密に行う。

### Security
- 環境変数ロード時に OS 環境変数を保護（protected set）して .env による上書きを防止する仕組みを実装。
- OpenAI API キーは api_key 引数で明示注入でき、未設定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError を返す（誤操作を早期検出）。

### Notes / Design decisions
- ルックアヘッドバイアス回避: 各種処理（news ウィンドウ、prices のクエリ、regime 判定など）で datetime.today()/date.today() を直接参照せず、外部から与えられる target_date の前後で厳密にデータを抽出。
- フェイルセーフ方針: AI API 失敗や不足データ時には例外で全体を止めるのではなく、フォールバック値（例: macro_sentiment=0.0）やチャンクスキップで継続する設計。
- OpenAI 呼び出しは JSON Mode を利用。レスポンスの頑健なパース（前後余計なテキストが混ざるケースへの復元）を実装。
- トランザクション: DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を用いた冪等書き込み。例外発生時は ROLLBACK を試行し、失敗時はログ出力。
- DuckDB のデータ型・互換性に配慮（date 変換、list バインドの不安定性回避等）。
- 多くの関数で「データ不足時は None を返す」「呼び出し側で不備を判断できるようにする」方針を採用。

### Known limitations
- OpenAI (gpt-4o-mini) の利用が前提。APIキーが未設定の場合は score_news / score_regime は ValueError を送出します。
- 一部のファクター（PBR・配当利回り等）は未実装。
- news_nlp/regime_detector は JSON Mode に依存しており、モデル側の出力形式変化に対して脆弱性が残る可能性がある（既にいくつかの復元処理を組み込んでいる）。
- DuckDB の特定バージョン依存の挙動（executemany の空配列等）に注意。

### Fixed
- なし（初回リリースのため）。

### Changed / Removed / Deprecated
- なし（初回リリースのため）。

---

この CHANGELOG はコードベースの公開 API と主要な設計方針を要約したものです。実装の詳細や使用例は各モジュールの docstring / ソースコメントを参照してください。