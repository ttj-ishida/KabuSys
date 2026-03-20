# Changelog

すべての大きな変更は Keep a Changelog の慣例に従って記載します。  
許容: 重大な変更 (Breaking)、追加 (Added)、変更 (Changed)、修正 (Fixed)、非推奨 (Deprecated)、削除 (Removed)、セキュリティ (Security)。

なお、本 CHANGELOG は提供されたコードベースから仕様・実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース。
- 基本パッケージ構成を追加:
  - kabusys.__init__ にバージョン情報と公開モジュールを定義。
  - 空の execution パッケージプレースホルダを追加。
- 環境設定管理 (kabusys.config):
  - .env/.env.local ファイルおよび OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、CWD 非依存で自動ロード可能。
  - .env パースの堅牢化（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須キー取得ヘルパー _require と Settings クラスを提供し、主要設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）を公開。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許可値の列挙）と is_live / is_paper / is_dev のブールプロパティを実装。
- データ取得・保存 (kabusys.data.jquants_client):
  - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - RateLimiter による固定間隔スロットリング（120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ処理を実装。429（Retry-After ヘッダ優先）や 408/5xx を再試行対象に含む。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識した実装。
  - 型変換ユーティリティ (_to_float, _to_int) を提供し、入力データの堅牢なパースを実現。
- ニュース収集 (kabusys.data.news_collector):
  - RSS ベースのニュース収集モジュールを追加。DEFAULT_RSS_SOURCES、受信最大サイズ制限（MAX_RESPONSE_BYTES）、URL 正規化・トラッキング除去、記事 ID に SHA-256（正規化後先頭 32 文字）を利用する方針を実装。
  - defusedxml を用いた XML パースで XML Bomb 等に対処する設計。
  - DB へのバルク挿入を想定したチャンク処理を導入（_INSERT_CHUNK_SIZE）。
- リサーチモジュール (kabusys.research):
  - ファクター計算ユーティリティ群を提供。calc_momentum, calc_volatility, calc_value を実装。
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）を実装。外部依存 (pandas 等) を使わず標準ライブラリ + DuckDB で完結する設計。
  - zscore_normalize は kabusys.data.stats として再エクスポート（__init__ でまとめて公開）。
- 戦略モジュール (kabusys.strategy):
  - 特徴量生成 (feature_engineering.build_features):
    - research 側で計算された生ファクターを取得し、ユニバースフィルタ（最低株価、20日平均売買代金）適用、Z スコア正規化（対象列指定）、±3 でクリップ、features テーブルへ日付単位の置換（トランザクション）で保存する処理を実装。
    - DuckDB を用いた原子性（BEGIN/COMMIT/ROLLBACK）を保証。
  - シグナル生成 (signal_generator.generate_signals):
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントスコアを計算して重み付き合算による final_score を算出。
    - デフォルト重み・閾値を定義し、ユーザー指定 weights の検証と正規化を行う。
    - Bear レジーム判定（ai_scores の regime_score 平均が負）で BUY シグナル抑制。
    - 保有ポジションのエグジット判定（ストップロス：-8% 以内、スコア低下）を実装し SELL シグナルを生成。
    - BUY/SELL を signals テーブルへ日付単位で置換（トランザクション）する冪等処理を実装。
- ロギングによる詳細な操作ログと警告出力を随所に追加（例: リトライ/スキップ/データ不足/ROLLBACK 失敗など）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- news_collector: defusedxml を採用して XML 関連の脆弱性（XML Bomb 等）に対処。
- news_collector: 受信サイズ上限（MAX_RESPONSE_BYTES）によりメモリ DoS を軽減。
- jquants_client: Authorization トークン管理と自動リフレッシュにより、認証取り扱いを明確化。

### Notes / Known limitations / TODO
- signal_generator._generate_sell_signals にて説明されているトレーリングストップ（peak_price 依存）や時間決済（保有日数 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date 等を持たせる必要あり。
- news_collector の実装は安全性に配慮したユーティリティ群を提供しているが、実際の RSS フィード取得・パースと DB への紐付け（news_symbols 等）の最終的な結合処理は別途の実装箇所が必要となる可能性がある。
- jquants_client のレート制御は単一プロセス内の固定間隔スロットリングを採用。分散環境や複数プロセスからの同時アクセスを想定する場合は追加の分散レートリミッタが必要。
- config の自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後や非標準レイアウトでは KABUSYS_DISABLE_AUTO_ENV_LOAD の設定や手動ロードが必要になる場合がある。
- DuckDB のテーブルスキーマ（features, signals, raw_prices, raw_financials, market_calendar, ai_scores, positions など）は本実装から推測されるが、正確なスキーマ定義は別途ドキュメント/マイグレーションで提供する必要あり。

--- 

作成者注: 本 CHANGELOG は渡されたコードから実装と設計意図を推測して作成しています。実際のリリース履歴や細かい変更履歴が存在する場合は、そちらを優先して正確な内容に差し替えてください。