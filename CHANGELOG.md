# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このファイルはコードベースから推測して自動生成しています — 実際のリリースノート作成時は必要に応じて調整してください。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初期リリース。日本株のデータ収集・特徴量計算・ニュース NLP・市場レジーム判定・カレンダー管理など、研究/ETL/AI を横断する基本的機能を実装。

### Added
- パッケージの基本構成
  - src/kabusys/__init__.py にて version = 0.1.0、主要サブパッケージ（data, research, ai, monitoring 等を想定）を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から探索する _find_project_root を提供。
    - 自動読み込みは OS 環境変数 -> .env.local -> .env の優先度で行う。既存 OS 環境変数は保護され、.env.local は上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途）。
  - .env パース機能の強化（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い）。
  - Settings クラスを提供し、アプリで利用する設定値をプロパティ経由で取得可能。
    - 必須変数取得時に未設定なら ValueError を送出する _require を実装。
    - 取得可能な設定例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の検証ロジック
      - is_live / is_paper / is_dev のヘルパー

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約し、銘柄単位にニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント評価を行う機能。
    - JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換して DB クエリに利用（calc_news_window）。
    - バッチ処理: 最大 20 銘柄 / API 呼び出し（_BATCH_SIZE）。
    - 各銘柄は最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レスポンスは JSON Mode を想定し、厳密な JSON、かつ "results": [{"code":"XXXX","score":0.0}, ...] を期待。レスポンス復元ロジック（前後余分テキストが混在する場合の {} 抽出）あり。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。非リトライエラーはスキップして続行。
    - スコアは ±1.0 にクリップ。API障害やパース失敗時は該当チャンクをスキップ（空辞書）し、処理できた銘柄のみ ai_scores テーブルへ DELETE→INSERT（部分失敗時も既存スコアを保護）。
    - テスト用に _call_openai_api を patch して差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。APIキー未指定時は ValueError。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - マクロニュースは kabusys.ai.news_nlp の calc_news_window を用いて抽出、OpenAI (gpt-4o-mini) により macro_sentiment を取得（最大 _MAX_MACRO_ARTICLES 件）。
    - LLM 呼び出しはリトライ/バックオフ実装。API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - ルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ利用、datetime.today() を使用しない）。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。APIキー未指定時は ValueError。

- Data（ETL / カレンダー / pipeline）
  - kabusys.data.pipeline / etl
    - ETL 実行結果を表す dataclass ETLResult を追加（to_dict, has_errors, has_quality_errors）。
    - 差分更新、バックフィル、品質チェックの方針を踏まえたユーティリティ（コード参照の設計方針）。
    - DuckDB のテーブル最大日付取得やテーブル存在確認などの内部ユーティリティを実装。
  - kabusys.data.calendar_management
    - JPX マーケットカレンダー管理機能。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供（DB の market_calendar がある場合はそれを優先し、未登録日は曜日ベースでフォールバック）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を更新。バックフィルや健全性チェック（未来日チェック）を実装。
    - DB がまばらな場合でも一貫性を保つ探索ロジック（最大探索日数制限 _MAX_SEARCH_DAYS）。
    - jquants_client（kabusys.data.jquants_client）との連携箇所を想定。

- Research（ファクター計算 / 特徴量探索）
  - kabusys.research.factor_research
    - Momentum, Volatility, Value, Liquidity 等のファクター計算を実装。
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB の SQL を活用して高効率に計算。結果は (date, code) をキーとした dict リストで返却。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定 horizon（営業日ベース）に対する将来リターンを一度に取得。horizons のバリデーション（正の整数、<=252）あり。
    - calc_ic: スピアマンランク相関（IC）を実装。十分なサンプル（>=3）でない場合は None。
    - rank: 同順位は平均ランクを付与するランク変換（浮動小数の丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- その他ユーティリティ
  - 各モジュールで DuckDB を想定（duckdb.DuckDBPyConnection パラメータ）。
  - OpenAI SDK（OpenAI クライアント）と統合し、モデル gpt-4o-mini をデフォルトで利用。
  - 多くの処理で「部分失敗を許容」し、他のデータや銘柄に影響を与えない方針（部分的な書き込み、ロールバック処理、ログ出力）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 注意: OpenAI API キーや各種トークンは必須項目扱いのプロパティがあるため、運用時は環境変数管理に注意。Settings._require は未設定時に ValueError を投げるため CI/デプロイでの安全チェックに利用可能。

### Notes / Operational
- OpenAI 呼び出しのフォールバック/クリップ/リトライの動作により、API 障害時でも処理が完全停止しない設計。ただし LLM 未取得分はスコア 0 またはスキップされるため、運用時の期待値に注意。
- .env の自動ロードはプロジェクトルート探索を行うため、パッケージ配布後も CWD に依存せずに動作する想定。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを止めることができる。
- DuckDB 特有の executemany 空リスト禁止などの挙動に対するガードを実装（空リストの場合は実行をスキップ）。

---

以上がコードベースから推測した初期リリース（0.1.0）の主な変更点・機能一覧です。リリースノートやユーザー向けドキュメント作成時は、実際のコミット履歴や CHANGELOG ポリシーに合わせて編集してください。