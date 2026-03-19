# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下はコードベースから推測される主要な追加点・設計上の意図・注意点です。

### Added
- パッケージ基本情報
  - パッケージ名/バージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理
  - .env ファイルや環境変数を自動読み込みする設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出 (.git または pyproject.toml に基づく) により CWD に依存しない自動ロード。
    - .env/.env.local の優先順位制御。既存 OS 環境変数を保護する protected ロジック。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env の柔軟なパース（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
    - 必須環境変数取得ヘルパー _require と Settings クラス（J-Quants / kabu / Slack / DB パス / 環境・ログレベル等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - デフォルト DB パス（duckdb/sqlite）の既定値提供。

- Data レイヤー（データ取得・保存）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - API レート制御（120 req/min）の固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大試行回数、429 の Retry-After 尊重）。
    - 401 発生時にリフレッシュトークンで自動トークン更新し 1 回リトライする安全設計。
    - ページネーション対応のフェッチ関数（fetch_daily_quotes, fetch_financial_statements）。
    - JPX カレンダー取得（fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ（_to_float, _to_int）で堅牢に変換し不正データを None として扱う。

  - ニュース収集（RSS）モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得（fetch_rss）と記事整形（preprocess_text）機能。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - defusedxml を使った安全な XML パース、防御的なパース失敗ハンドリング。
    - SSRF 対策：URL スキーム検証、ホストがプライベート/ループバック/リンクローカルでないことの検査、リダイレクト時の検査ハンドラ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去・クエリソートによる URL 正規化。
    - DB へのバルク保存関数（save_raw_news, save_news_symbols, _save_news_symbols_bulk）をトランザクションで実行し、INSERT ... RETURNING を使用して実際に追加された件数を返却。
    - 銘柄コード抽出機能（extract_stock_codes）および全ソース収集ジョブ run_news_collection（既知銘柄セットによる紐付け）。

- Research（特徴量・ファクター計算）
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：指定日から複数ホライズン（既定 [1,5,21]）の将来リターンを一度のクエリで取得する設計。
    - Information Coefficient（IC）計算（calc_ic）：スピアマンランク相関を標本のランク計算を通じて算出（ties は平均ランクで処理）。有効サンプルが少ない場合は None を返す。
    - ランク変換ユーティリティ（rank）とファクター統計要約（factor_summary）。
    - 標準ライブラリのみで実装する方針（pandas 等に依存しない実装）。

  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（calc_momentum）：1M/3M/6M リターン、MA200 乖離率を計算。ウィンドウ内の行数不足時は None。
    - ボラティリティ/流動性（calc_volatility）：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range 計算時の NULL 伝播制御を実装。
    - バリュー（calc_value）：raw_financials と prices_daily を組み合わせて PER/ROE を算出（EPS 0/欠損は None）。
    - 計算において DuckDB のウィンドウ関数を活用し、過去スキャン範囲にバッファを持たせて堅牢に取得。

- DB スキーマ（部分実装）
  - DuckDB 用の DDL 定義（src/kabusys/data/schema.py）を追加。Raw レイヤーのテーブル定義（raw_prices, raw_financials, raw_news, raw_executions の一部）を含む。

### Security
- ニュース収集における安全対策
  - defusedxml を用いた XML パーサにより XML 関連の脆弱性（XML bomb 等）を緩和。
  - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホスト/IP のプライベートアドレス判定、リダイレクト先の事前検証ハンドラを実装。
  - レスポンスサイズの上限チェック（MAX_RESPONSE_BYTES）と gzip 解凍後の再チェックによるメモリ DoS 防止。
  - _validate_url_scheme / _is_private_host により外部アクセスの検査を追加。

- J-Quants クライアントでの認証・再試行
  - 401 時の安全なトークンリフレッシュ（1回のみの自動リフレッシュ）と無限再帰回避設計（allow_refresh フラグ）。
  - ネットワーク・HTTP エラーに対する再試行ポリシー（429 の Retry-After 優先、指数バックオフ）。

### Performance / Reliability
- API 呼び出しのスロットリング（_RateLimiter）によりレート制限を遵守。
- J-Quants フェッチ関数はページネーションを考慮して複数ページを結合取得。
- データ保存はバルク/チャンク化（news では _INSERT_CHUNK_SIZE）とトランザクションで実行しオーバーヘッドを削減。
- DuckDB 側のクエリではホライズンをまとめて取得したり、ウィンドウ関数で一度に必要な値を算出することで SQL 回数を削減。
- モジュールレベルで ID トークンをキャッシュしページネーション間で再利用（_ID_TOKEN_CACHE）。

### Internal / Implementation notes
- 多くの関数は prices_daily / raw_financials / raw_news 等の DuckDB テーブルを参照する想定で実装されており、本番発注 API へのアクセスは行わない設計（研究・特徴量算出の分離）。
- research モジュール群は外部依存を避け、ユニットテストしやすい設計（標準ライブラリベース）。
- .env のパースは export プレフィックス、クォート内のエスケープ、インラインコメントなど現実的な .env の記述に耐えうる実装。
- save_* 系の関数は PK 欠損行のスキップやスキップ件数ログ出力を行いデータ不整合に耐性を持たせている。

### Breaking Changes
- 初回リリースにつき破壊的変更はありません。

### Migration / Setup notes
- 必須の環境変数（少なくとも以下を設定する必要あり）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DB のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env 読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（値は任意だが存在するだけで無効化）。

### Notes / 今後の想定改善点（コードからの推測）
- schema モジュールは Execution レイヤー等の完全な DDL をまだ未完備の可能性があるため、マイグレーション/初期化ロジックの完成が想定される。
- strategy / execution / monitoring パッケージは __init__.py のみで中身が空のため、実運用向けの戦略実装・発注ラッパ等の追加が必要。
- research モジュールは pandas 等を使わない実装だが、大規模データ処理では速度面でライブラリ導入の検討余地あり。

---

この CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートとして使用する場合は機能追加・修正点・作者情報・既知の問題などをプロジェクト関係者と照合のうえ更新してください。