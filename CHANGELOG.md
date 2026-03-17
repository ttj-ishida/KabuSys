CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- （なし）

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース。パッケージ名: KabuSys (バージョン 0.1.0)。
- パッケージ初期化:
  - src/kabusys/__init__.py による基本公開 API 定義（data, strategy, execution, monitoring）。
- 環境設定管理:
  - src/kabusys/config.py を追加。
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を提供。
  - export KEY=val 形式やシングル/ダブルクォート、インラインコメント、エスケープ等に対応した .env パーサーを実装。
  - OS 環境変数保護（protected set）機能により .env の上書きを制御。
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル判定などのプロパティを提供）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live/is_paper/is_dev 判定。

- J-Quants API クライアント:
  - src/kabusys/data/jquants_client.py を追加。
  - レート制限制御（固定間隔スロットリング）を持つ内部 RateLimiter 実装（120 req/min に準拠）。
  - リトライ戦略（指数バックオフ、最大 3 回、HTTP 408/429/5xx に対応）。
  - 401 応答時は自動でリフレッシュトークンから id_token を再取得して 1 回リトライ（無限再帰防止）。
  - id_token のモジュールレベルキャッシュを導入し、ページネーション間で再利用。
  - JSON デコード失敗時の明示的エラー報告。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足 / OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ: _to_float, _to_int（不正値や空値を安全に扱う）。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止。

- ニュース収集モジュール:
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィード取得・パース機能（defusedxml を利用して XML 攻撃を防止）。
  - セキュリティ対策:
    - HTTP リダイレクト時のスキーム検証・プライベートアドレス（SSRF）検出を行うカスタム RedirectHandler を実装。
    - 初期 URL と最終 URL のホストを検証し、プライベートアドレス（ループバック/リンクローカル/プライベート/マルチキャスト）を拒否。
    - URL スキーム制限（http/https のみ許可）。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
  - テキスト前処理（URL 除去・空白正規化）。
  - DB 保存:
    - save_raw_news: chunk 単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入 ID を返す（トランザクション内で実行）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複をスキップ、INSERT ... RETURNING を用いる）。
  - 銘柄コード抽出（4桁数字パターン、既知銘柄セットでフィルタリング）を実装。
  - run_news_collection: 複数 RSS ソースを個別にフェッチして DB 保存・銘柄紐付けまで行う統合ジョブ（ソース単位でエラーハンドリングし、1 ソース失敗でも他ソースを継続）。

- DuckDB スキーマ定義と初期化:
  - src/kabusys/data/schema.py を追加。
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を包括的に用意:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種チェック制約（NOT NULL, CHECK 等）や外部キー、主キーを定義。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ作成、DDL 実行、インデックス作成を行い接続を返す。get_connection() を提供。

- ETL パイプライン基礎:
  - src/kabusys/data/pipeline.py を追加（ETL の骨組み）。
  - ETLResult dataclass による実行結果の集約（品質問題・エラー一覧を含む）。
  - 差分更新ヘルパー（テーブル存在確認、最大日付取得）。
  - 市場カレンダーを用いた営業日調整 (_adjust_to_trading_day)。
  - 差分更新の実装方針（最終取得日から backfill する、デフォルト backfill_days=3）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパー。
  - run_prices_etl の骨組み（差分取得→jquants_client 経由で取得→save して保存件数を返却）。※ run_prices_etl は差分更新のロジックを備える（詳細はコード中）。

- その他:
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py を配置（パッケージの準備）。

Security
- RSS パーサで defusedxml を採用し、XML 関連の攻撃を緩和。
- RSS フェッチで SSRF 対策（スキーム検証、ホストがプライベートアドレスかを判定、リダイレクト先の事前検査）を実装。
- ネットワーク読み取りサイズ上限と gzip 解凍後サイズ検査によりメモリ DoS を軽減。

Notes / Known issues
- ETL パイプラインや品質チェック部分（quality モジュールの呼び出し等）は骨組みを提供しており、個別のチェック実装や運用ポリシーは今後の拡張対象です。
- run_prices_etl を含む一部関数は引数注入（id_token 等）によりテスト容易性を配慮していますが、リリース時点では更なるユニット／統合テストの追加が推奨されます。

導入・移行メモ
- 初回利用時は init_schema(db_path) を呼んで DuckDB スキーマを作成してください。
- 環境変数は .env/.env.local または OS 環境で設定可能。テスト等で自動ロードを停止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants 用リフレッシュトークン（JQUANTS_REFRESH_TOKEN）や Slack トークン等の必須環境変数は Settings を通して参照され、未設定時は例外が発生します。

---