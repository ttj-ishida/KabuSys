CHANGELOG
=========
すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従っています。  

注: この CHANGELOG は提供されたソースコードの内容から推測して作成しています。

Unreleased
----------
- なし

[0.1.0] - 2026-03-17
--------------------
初回リリース。日本株の自動売買プラットフォーム「KabuSys」のコアモジュールを実装。

Added
- パッケージ構成
  - パッケージ名: kabusys、エクスポート: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から親ディレクトリを探索（配布後の実行でも安定）。
  - .env パーサー: export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント対応。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護（protected）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants、kabuAPI、Slack、DB パス、環境種別、ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を列挙し不正な場合は ValueError を送出）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - /token/auth_refresh による ID トークン取得 (get_id_token)。
  - API リクエスト共通処理 (_request) を実装:
    - レート制限を守る固定間隔スロットリング（120 req/min）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key 利用）で全件取得。
    - JSON デコードエラー時の明示的なエラーメッセージ。
  - データ取得関数:
    - fetch_daily_quotes: 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データを取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等設計 -> ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias のトレースを容易に。
  - モジュールレベルの ID トークンキャッシュを保持しページネーション間で再利用。
  - 型変換ユーティリティ: _to_float, _to_int（不正値・空値を安全に None に変換）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する一連の処理を実装。
  - セキュリティ対策:
    - defusedxml による XML パースで XML Bomb 等に耐性。
    - HTTP リダイレクトごとにスキームとホストを検査するカスタム RedirectHandler（内部ネットワークへの到達を防止）。
    - URL スキーム検証（http/https のみ許可）とプライベート/ループバックアドレス検出（SSRF 対策）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 非標準スキーム（mailto:, file: 等）のリンクを弾く。
  - 正規化 & 前処理:
    - _normalize_url: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント除去、クエリソート。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を確保。
    - preprocess_text: URL 除去、空白正規化。
    - RSS pubDate の堅牢なパース（タイムゾーンを UTC に正規化）、失敗時は代替時刻を利用。
  - DB 保存:
    - save_raw_news: チャンク単位のバルク INSERT + RETURNING を使用し、実際に挿入された記事 ID を返す（ON CONFLICT DO NOTHING）。
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄コードの紐付けを一括保存（重複排除・チャンク・トランザクション管理）。
  - 銘柄コード抽出:
    - extract_stock_codes: テキストから 4 桁の銘柄コード候補を抽出し、known_codes に含まれるものだけ返す（重複除去）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）と Execution 層のテーブル DDL を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種 CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義（データ整合性重視）。
  - クエリ最適化のためのインデックス定義（頻出パターンに基づく）。
  - init_schema(db_path): 親ディレクトリ自動作成、全テーブル・インデックスを冪等に作成して接続を返す。
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を実装し ETL 結果・品質問題・エラーを集約。
  - 差分更新ヘルパー:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - 市場カレンダー関連:
    - _adjust_to_trading_day: 非営業日を直近の営業日に調整するロジック（フォールバックあり）。
  - run_prices_etl: 株価日足の差分 ETL 実装方針（差分更新、backfill_days による後出し修正吸収、保存は jq.save_daily_quotes を利用）。
  - ETL 設計方針:
    - 差分更新デフォルト単位は営業日 1 日分。
    - backfill_days による再取得。
    - 品質チェックは Fail-Fast ではなく検出情報を返す方針（quality モジュールと連携想定）。
    - id_token を注入可能にしテスト容易性を確保。

Security
- SSRF 対策を強化:
  - リダイレクト毎のスキーム／ホスト検証、初回 URL のホスト事前検証、プライベートアドレス検出によるスキップ。
- XML パースに defusedxml を採用。
- レスポンス長の上限や gzip 解凍後のチェックを導入しメモリ DoS / Gzip bomb に対処。
- 環境変数の自動ロードで OS 環境変数を保護（.env による上書きを制限）。

Performance / Reliability
- API レート制限（120 req/min）を守るレートリミッタを実装。
- リクエストのリトライ（指数バックオフ・Retry-After 尊重）により一時的な失敗からの回復を図る。
- DuckDB へのバルク挿入をチャンク化してパフォーマンスと SQL 長制限を考慮。
- INSERT ... RETURNING を使って実際に挿入された件数を正確に取得。

Documentation
- 各モジュールに詳細な docstring を追加（設計方針、処理フロー、引数説明、戻り値説明、例外条件など）。

Known issues / Notes
- run_prices_etl の末尾の戻り値が提供されたコード断片では途中で切れている（"return len(records), " のように見える）。実運用では (fetched_count, saved_count) のタプルを返す意図と推測されるため、最終リターンの実装確認が必要。
- strategy, execution, monitoring パッケージの __init__ は存在するが、具体的な実装はこのリリースのコード断片には含まれていない（今後の実装予定）。
- quality モジュール参照はあるが実装は含まれていないため、品質チェックの具体的ロジックは別実装を想定。

Acknowledgments / Other
- この CHANGELOG はソースコードのコメント・docstring から推測して作成しています。実際のリリースノート作成時はコミットログ・リリース作業の記録を参照してください。