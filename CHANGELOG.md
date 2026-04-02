# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」スタイルに準拠しています。  
バージョン番号はパッケージの src/kabusys/__init__.py の __version__ に対応します。

## [0.1.0] - 2026-04-02

初回公開リリース。本リリースはデータ取得（ETL）・カレンダー管理・リサーチ（ファクター計算）・AI ニュース解析・市場レジーム判定・設定管理などのコア機能群を含みます。

### Added
- パッケージ基礎
  - パッケージ名 kabusys、バージョン 0.1.0 を追加。
  - top-level の __all__ に data, strategy, execution, monitoring を公開（将来モジュール用の整理済みエクスポート）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数を自動で読み込む機能を実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを抑止可能。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（条件付き）等に対応。
  - 環境変数必須チェック用 _require と Settings クラスを実装。主要設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須に設定。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等のデフォルトを提供。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーションを実装。
    - is_live / is_paper / is_dev の判定プロパティを追加。
- AI ニュース解析 (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を生成する score_news を実装。
  - 機能・設計のポイント:
    - スコアリング対象ウィンドウは JST 基準で「前日 15:00 〜 当日 08:30」を採用（UTC に変換して DB と比較）。
    - 1銘柄あたり最新記事を最大 _MAX_ARTICLES_PER_STOCK 件、かつ文字数トリム（_MAX_CHARS_PER_STOCK）でまとめる。
    - 1 API コールあたりのバッチサイズは _BATCH_SIZE（デフォルト 20）で分割。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。その他のエラーはスキップし処理継続（フェイルセーフ）。
    - OpenAI の JSON Mode を利用し、レスポンスの検証・クリーニング（余分な前後テキストの {} 抽出等）を実施。
    - スコアを ±1.0 にクリップ。
    - 書き込みは部分置換（DELETE → INSERT）で冪等性を確保し、DuckDB の executemany 空リスト制約に対応したガードを実装。
    - テスト容易性のため OpenAI 呼び出しを _call_openai_api 関数経由で差し替え可能。
- レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - 機能・設計のポイント:
    - ma200_ratio の算出は target_date 未満のデータのみを利用しルックアヘッドを防止。
    - マクロ記事の抽出はニュースタイトルをマクロキーワードでフィルタ（最大 _MAX_MACRO_ARTICLES 件）。
    - OpenAI 呼び出しは gpt-4o-mini を想定。API 障害やパース失敗時は macro_sentiment=0.0 にフォールバックして処理継続（フェイルセーフ）。
    - レジームのスコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時はロールバックを試行。
    - テスト用に _call_openai_api を差し替え可能。
- データ ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを実装し、ETL 実行の集計（取得数 / 保存数 / 品質問題 / エラー）を表現。
  - _table_exists / _get_max_date 等の内部ユーティリティを実装（DuckDB 操作用）。
  - ETL の設計方針として差分取得・バックフィル・品質チェック（重大度を区別）を採用。
  - kabusys.data.etl で ETLResult を再エクスポート。
- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を用いた営業日判定ロジックとユーティリティを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
  - calendar_update_job を実装し J-Quants API クライアント経由で JPX カレンダーを差分取得・バックフィルして保存する機能を提供。
  - DB 登録値優先、未登録日は曜日（平日/週末）ベースのフォールバックを行い、DB がまばらな場合でも一貫した判定を返す。
  - 極端な将来日付に対する健全性チェックやバックフィルポリシーを実装。
- リサーチ（ファクター計算） (kabusys.research)
  - ファクター計算群を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - calc_value: raw_financials から PER、ROE を算出（EPS が 0/欠損のときは None）。
  - 特徴量探索・統計ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（最小 3 レコード未満は None）。
    - rank: 同順位は平均ランクを返す安定したランク付け実装（浮動小数点の丸め対策を含む）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を標準ライブラリのみで計算。
  - 設計方針:
    - DuckDB 接続を受け取り SQL と標準ライブラリで処理。外部ライブラリ（pandas 等）に依存しない。
    - 本モジュールは本番発注 API にアクセスしない（データ参照のみ）。
- パッケージ初期化のエクスポート整理
  - kabusys.ai.__init__ で score_news を公開。
  - kabusys.research.__init__ で主要関数群を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の必須チェックを行い、API キーやトークンが未設定の場合は明示的に ValueError を発生させることで意図しない実行を防止。
- .env 読み込み時に OS 環境変数を protected として上書きを防止する仕組みを実装。

### Notes / 実装上の留意点
- ルックアヘッドバイアス対策:
  - 全ての AI/リサーチ処理は date / target_date を明示指定し、datetime.today() / date.today() を直接参照しない設計。
  - DB クエリは target_date 未満・以前等の排他条件を用いて将来データ参照を回避。
- フェイルセーフ:
  - OpenAI 呼び出し失敗時は例外をスローせず、スコアを 0.0 として継続するか該当チャンクをスキップする方針。
- テスト性:
  - AI モジュールの OpenAI 呼び出しは内部の _call_openai_api を patch することでモック可能。
- DuckDB 互換性:
  - executemany の空リストバインドなど DuckDB のバージョン差に起因する問題に対するガードを実装（空チェック）。
- 外部 API クライアント（J-Quants / OpenAI）は明示的にインジェクション可能な設計や差し替えポイントを確保している（jquants_client 経由呼び出し、OpenAI ラッパーの差し替えなど）。

### Deprecated
- （初回リリースのため該当なし）

---

今後のリリースでは、strategy / execution / monitoring モジュールの実装・統合、より詳細な品質チェックルール、テストカバレッジの拡充、エラーメトリクスの収集・通知機能（Slack 連携強化等）を予定しています。