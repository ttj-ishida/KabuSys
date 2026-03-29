# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルでは、リリースごとの主要な追加・変更点、既知の制限や設計上の意図を記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回公開リリース。日本株のデータ取得・ETL・カレンダー管理・リサーチ・AI によるニュース評価・市場レジーム判定までを含む基盤ライブラリを提供します。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = "0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 読み込み（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等をサポート。
    - .env.local を override=True で読み込み、OS 環境変数は protected として上書きを防止。
  - 必須環境変数取得用の _require ヘルパー（未設定時は ValueError）。
  - 設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へ JSON Mode で送信してセンチメントを算出する score_news を実装。
  - タイムウィンドウ（JST）計算: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB クエリに利用。calc_news_window を提供。
  - バッチ処理: 銘柄を最大 _BATCH_SIZE=20 件ずつ送信、1銘柄あたり _MAX_ARTICLES_PER_STOCK=10 件・_MAX_CHARS_PER_STOCK=3000 文字でトリム。
  - 再試行（Backoff）ロジック: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ（最大回数設定あり）。
  - レスポンス検証: JSON パース、"results" 配列の存在チェック、各要素の code/score 検証、未知コードは無視、スコアは ±1.0 にクリップ。
  - 部分成功に配慮した DB 書き込み（対象コードのみ DELETE → INSERT）により部分失敗時に既存スコアを保護。
  - API 呼び出し箇所はテストで差し替え可能（_unittest.mock で _call_openai_api をパッチ可能）。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次判定を行う score_regime を実装。
  - マクロニュース抽出は news_nlp.calc_news_window と raw_news を利用、マクロキーワードによるフィルタを実施。
  - OpenAI 呼び出しは独立実装（news_nlp と private 関数を共有しない設計）でリトライ／フェイルセーフ（API 失敗時は macro_sentiment = 0.0）を行う。
  - レジームスコアのラベリング: score >= 0.2 → "bull", <= -0.2 → "bear", それ以外 → "neutral"。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 偏差（データ不足時は None）。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio。
    - calc_value: raw_financials から EPS/ROE を取り込み PER / ROE を計算（EPS=0 や欠損時は None）。
    - すべて DuckDB SQL ベースで計算し、(date, code) をキーとする dict のリストを返す。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり（正の整数、<=252）。
    - calc_ic: スピアマン（ランク）相関の計算。必要レコード数が少ない場合は None を返す。
    - rank: 同順位は平均ランクにするランク付け実装（round(v, 12) による丸めで ties の漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の集計を実装。
  - 外部ライブラリに依存せず、標準ライブラリ + DuckDB で完結する設計。

- データ / カレンダー管理（kabusys.data）
  - calendar_management:
    - market_calendar を用いた is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 未取得時は曜日ベース（土日を非営業日）でフォールバック。DB 登録値が優先される一貫した振る舞い。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等保存。バックフィル期間と健全性チェックを実装（未来日が異常に大きい場合はスキップ）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）で無限ループを防止。
  - pipeline / etl:
    - ETLResult データクラスを提供（取得/保存件数、品質チェック、エラー一覧などを保持）。
    - ETL パイプライン設計方針に基づく差分取得、backfill、品質チェックの仕組み（jquants_client および quality モジュールと連携する設計）。
    - 内部ユーティリティ: _table_exists / _get_max_date など。

- その他
  - data.etl で ETLResult を再エクスポート。
  - research パッケージで zscore_normalize を data.stats からインポートして公開。
  - モジュール内ログ出力（logger）を適切に配置し、デバッグ情報や WARN/INFO を出力。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数管理において OS 環境変数の上書きを防ぐ保護機構（protected set）を実装し、.env.local による意図しない上書きを抑止する仕組みを導入。

### Notes / Known limitations / 実装上の意図
- ルックアヘッドバイアス回避:
  - AI モジュール（news_nlp, regime_detector）やリサーチ関数はいずれも内部で datetime.today() / date.today() を参照せず、呼び出し側から渡された target_date に対してのみ処理を行う設計になっています。
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時は例外を投げず（あるいは局所的に 0.0 を返す/スキップする）処理を継続して、システム全体の停止を避ける設計です。呼び出し側は戻り値・返り値件数で失敗を検出可能です。
- テスト容易性:
  - OpenAI 呼び出し部分はモジュール内 private 関数として切り出してあり、unittest.mock.patch により差し替え可能。DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護される。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン問題を考慮し、空チェックを行ってから executemany を実行する箇所があります。
- 外部クライアント実装は別モジュール（kabusys.data.jquants_client 等）に委譲しているため、J-Quants / kabu API 実際の呼び出しはそこを差し替えることで実環境向けに設定可能。
- 日時/タイムゾーン:
  - DB 保存は raw_news.datetime が UTC 想定、ニュースウィンドウ計算は JST を基準にして UTC naive datetime を生成する仕様です。呼び出し側はこの前提を満たすこと。

もし、より詳細なリリースノート（各関数の使用例や API シグネチャの説明、互換性注意点など）をご希望であれば、用途に応じてセクションを追加して作成します。