# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-27

初回リリース。

### Added
- パッケージ初期構成
  - kabusys パッケージを追加。公開 API: data, strategy, execution, monitoring。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定・自動 .env 読み込み（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサは export 形式・クォート・エスケープ・インラインコメント等に対応。
  - 環境変数必須チェック用の Settings クラスを提供。主な設定キー:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）
  - OS 環境変数は protected として .env による上書きを防止。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し、ai_scores テーブルへ書き込み。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST に対応（内部は UTC naive で扱う）。
  - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
  - OpenAI 呼び出しは JSON Mode を利用。レスポンスのバリデーション（results リスト・コード照合・数値チェック）を実装。
  - リトライ／バックオフ: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ（最大 retry 回数）でリトライ。
  - フェイルセーフ: API 呼び出しやパース失敗時は当該チャンクをスキップし、処理は継続。
  - 書き込みは部分失敗に備え、処理済みコードのみ DELETE → INSERT で置換（冪等性確保）。
  - テスト用に _call_openai_api をパッチ差し替え可能。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して daily market_regime テーブルへ書き込み。
  - ma200_ratio の計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを排除。
  - マクロ記事抽出はマクロキーワード群に基づき最大 20 件まで取得。記事がない場合は LLM を呼ばず macro_sentiment=0.0。
  - OpenAI は gpt-4o-mini を使用、JSON パース失敗や API エラー時は macro_sentiment を 0.0 にフォールバック（WARN ログ）。
  - レジームスコアはクリップして -1..1 に収め、閾値で 'bull' / 'neutral' / 'bear' をラベル化。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT による冪等操作。失敗時は ROLLBACK を試みる。

- データプラットフォーム関連（src/kabusys/data/*）
  - calendar_management:
    - JPX カレンダーを扱うユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar にデータがない場合は曜日ベース（週末を休日扱い）でフォールバック。
    - calendar_update_job(conn, lookahead_days=90): J-Quants からの差分取得 → market_calendar へ保存（バックフィル・健全性チェックを含む）。
  - pipeline:
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラー等を集約）。
    - ETL 実装方針: 差分更新、バックフィル、品質チェックの取り込み、idempotent な保存。
  - etl モジュールは ETLResult を再エクスポート。

- リサーチ機能（src/kabusys/research/*）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離等を計算（データ不足は None）。
    - calc_volatility(conn, target_date): 20 日 ATR, 相対 ATR, 平均売買代金, 出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS=0 の場合は None）。
    - 計算は DuckDB SQL を用い、prices_daily/raw_financials のみ参照。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターンを一クエリで取得（horizons バリデーションあり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（有効行数 3 未満は None）。
    - rank(values): 同順位は平均ランクで処理。
    - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリーを返す。
  - research パッケージはユーティリティを再エクスポートして使いやすく整理。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- OpenAI API キー（OPENAI_API_KEY または各関数の api_key 引数）および各種トークン（JQUANTS_REFRESH_TOKEN 等）を環境変数で管理することを想定。
- .env 読み込みは OS 環境変数を保護する仕組み（protected keys）を持つ。

### Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス対策: datetime.today()/date.today() を分析関数内で直接参照しない設計（target_date を明示的に渡す）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスパースの頑健化（余分な前後テキストの復元）を実装。
- API 呼び出しはリトライ／指数バックオフ戦略を採用。5xx と 429/タイムアウト/接続断はリトライ対象。
- DB 書き込みは冪等化を重視（DELETE→INSERT、ON CONFLICT 相当の扱い）。
- テスト容易性を考慮し、OpenAI 呼び出し点は明示的に差し替え可能にしている（unittest.mock.patch 想定）。
- 外部依存は最小化（DuckDB 使用、外部ライブラリに過度に依存しない実装方針）。

もし追加で記載してほしい差分（例: リリース日を別にする、より詳細な実行例や既知の制約事項など）があれば教えてください。