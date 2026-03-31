# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]
（次リリースに向けた項目はここに記載）

## [0.1.0] - 2026-03-31
初回公開リリース

### Added
- パッケージ全体
  - 初期パッケージ `kabusys` を追加。モジュール群（data, research, ai, config, 等）を公開。
  - パッケージバージョンを `0.1.0` に設定。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを実装。
  - 自動.env読み込み機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込む（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - 読み込み順序: OS環境変数 > .env.local > .env。`.env.local` は上書き（override）を行うが、OS環境変数は保護される（protected）。
    - .env パーサは `export KEY=val`、単一/二重クォート、バックスラッシュエスケープ、コメント（インラインコメントの扱い）などに対応した堅牢な実装。
  - 必須設定取得ヘルパ `_require` を提供（未設定時は ValueError を送出）。
  - 許容値チェック:
    - `KABUSYS_ENV`（development / paper_trading / live）と `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。

- AI モジュール (`kabusys.ai`)
  - ニュースNLU/センチメントスコアリング (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols を基に、指定日の前日15:00 JST〜当日08:30 JSTのニュースを対象に銘柄ごとのセンチメントを算出する `score_news(conn, target_date, api_key=None)` を実装。
    - OpenAI（gpt-4o-mini）を JSON mode で利用し、最大20銘柄/チャンクでバッチ処理。1銘柄あたりの記事上限件数（10件）・文字数上限（3000文字）でトリム。
    - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。その他エラーはスキップ（フェイルセーフ）。
    - レスポンスバリデーションを厳格化（JSON 抽出、results 配列、code/score の検査、スコアの数値化と ±1.0 でクリップ）。
    - 取得したスコアは部分冪等な方式で `ai_scores` テーブルへ書き込み（該当コードのみ DELETE → INSERT）。DuckDB の executemany の挙動に配慮。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（`_call_openai_api` 関数を patch 可能）。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
    - DuckDB の `prices_daily` / `raw_news` を参照して MA200 乖離を算出し、マクロニュースは `news_nlp.calc_news_window` でウィンドウを取得して最大20記事を LLM に評価させる。
    - OpenAI 呼び出しはリトライ実装を含む（429/接続失敗/タイムアウト/5xx の場合の再試行、失敗時は macro_sentiment=0.0 のフェイルセーフ）。
    - 結果は `market_regime` テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- データ処理 / ETL (`kabusys.data`)
  - ETL パイプラインインターフェース `ETLResult` を公開（`kabusys.data.pipeline.ETLResult` を `kabusys.data.etl` で再エクスポート）。
  - `kabusys.data.pipeline`:
    - 差分更新、バックフィル、品質チェック（`kabusys.data.quality` と連携）を想定した ETLResult と内部ユーティリティを実装。
    - DuckDB 上で最終日取得・日付範囲計算等を行うユーティリティを提供。
    - 設計上、致命的エラーが発生しても品質チェックは収集を継続し、呼び出し元で判断できるようにする（Fail-Fast ではない）。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダー（祝日・半日取引・SQ日）を扱うユーティリティを実装。
    - 営業日判定・前後営業日取得・期間内営業日列挙（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar が未取得の際は曜日ベースのフォールバック（週末を非営業日）を行い、DB のまばらな登録状況でも一貫した挙動を提供。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得・バックフィル・健全性チェックを実施）。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - `calc_momentum`, `calc_volatility`, `calc_value` を実装。
    - Momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）。
    - Volatility/Liquidity: 20日 ATR、ATR比率、20日平均売買代金、出来高比率（必要行数未満は None）。
    - Value: raw_financials から最も新しい財務データを取得して PER, ROE を算出（EPS が 0/欠損の場合は None）。
    - 出力は (date, code) をキーとする dict のリスト形式で返却。
  - 特徴量探索・統計 (`kabusys.research.feature_exploration`)
    - `calc_forward_returns`: target_date から指定ホライズン（営業日）先の将来リターンを一括で取得。
    - `calc_ic`: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル数が少ない場合は None を返す。
    - `rank`: 同順位は平均ランクを返すランク関数（丸めで ties 問題を軽減）。
    - `factor_summary`: 各ファクターカラムの count/mean/std/min/max/median を計算。
    - これらは外部ライブラリに依存せず、標準ライブラリのみで実装。

- テスト性・堅牢性設計
  - LLM 呼び出し部（_call_openai_api）はテスト用に patch 可能な実装とし、ユニットテストでモックしやすい設計。
  - ルックアヘッドバイアス防止のため、すべてのスコアリング関数は内部で datetime.today()/date.today() を安易に参照せず、明示的に target_date を受け取る設計。
  - DuckDB 操作はトランザクションを利用した冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK のフォールバックを備える。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数（API キー等）は Settings 経由で取得することを想定。自動 .env ロードはプロジェクトルート検出に依存し、必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

補足（公開 API の抜粋）
- kabusys.config.settings: 設定オブジェクト（jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
- kabusys.data.ETLResult（kabusys.data.etl 経由での再エクスポート）

もし CHANGELOG に含めたい追加の注記（既知の制限やリリース時の注意点）があれば教えてください。コードから推測した既知事項や注意点をさらに明確に追記します。