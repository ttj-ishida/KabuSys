CHANGELOG
=========

すべての変更は Keep a Changelog の書式に準拠しています。互換性のあるバージョニング（SemVer）を採用しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-18
--------------------

Added
- 初期リリース: 日本株自動売買システム "KabuSys" の基礎モジュールを追加。
  - パッケージ初期化: src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にルートを探索し、自動で .env /.env.local を読み込む仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサー強化:
    - export KEY=val 形式対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、コメント取り扱いのルール整備。
    - .env.local を優先的に上書きし、OS 環境変数（読み込み時点）を保護する protected 機能。
  - 設定プロパティ群（J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャネル、DB パス、環境/ログレベル検証など）を追加。env/log level の検証を実装し不正値で例外を出す。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ実装（_request）。JSON デコード、タイムアウト、クエリ生成、POST ボディ対応。
  - レート制御: 固定間隔スロットリングで 120 req/min を守る _RateLimiter を実装。
  - リトライ／バックオフ: 指数バックオフ、最大リトライ回数、HTTP ステータス（408/429/5xx）に対する挙動を実装。429 の場合は Retry-After を優先。
  - 認証トークン管理: get_id_token、モジュールレベルの ID トークンキャッシュ（ページネーション間共有）と 401 発生時の自動リフレッシュ（1 回のみ）を実装。
  - データ取得: 日足（fetch_daily_quotes）、財務四半期データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）をページネーション対応で実装。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。fetched_at を UTC で記録し、ON CONFLICT ... DO UPDATE を使って重複更新を制御。
  - 型変換ユーティリティ（_to_float/_to_int）を実装し、空値や不正値を安全に扱う。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と raw_news/raw_news_symbols への保存フローを実装。
  - セキュリティ強化:
    - defusedxml を使用して XML Bomb 等の脆弱性を軽減。
    - SSRF 対策: リダイレクト時にスキームとホスト/IP の検証を行う _SSRFBlockRedirectHandler、初回ホスト事前検証、_is_private_host によるプライベートアドレス検出（IP 直接判定＋DNS解決で A/AAAA を確認）。
    - 許可スキームは http/https に限定。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査でメモリ DoS を防止。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）を削除、スキーム/ホスト小文字化、フラグメント削除、クエリソートを行う _normalize_url を実装。
  - 記事 ID 生成: 正規化 URL の SHA-256 ハッシュ先頭 32 文字を記事IDとして生成（冪等性確保）。
  - テキスト前処理: URL 除去、空白正規化を行う preprocess_text を実装。
  - RSS パース: content:encoded の優先利用、pubDate のパース（RFC 2822 を UTC naive に変換、失敗時は警告して現在時刻を代替）を行う fetch_rss を実装。XML パース失敗は警告して空リストを返す。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのみを返す（チャンク化と1トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクでトランザクションにより保存し、実際に挿入された件数を返す。
  - 銘柄コード抽出: 4桁数字パターンから既知銘柄セットのみ返す extract_stock_codes を実装。
  - テスト容易性: _urlopen をラップしてテスト時にモック可能にしている。
- DuckDB スキーマ (src/kabusys/data/schema.py)
  - DataSchema.md に基づき 3 層（Raw / Processed / Feature / Execution）でテーブル定義を実装。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 制約・チェック (CHECK / PRIMARY KEY / FOREIGN KEY) を定義してデータ整合性を担保。
  - インデックス群（頻出クエリ向け）を作成する DDL を追加。
  - init_schema(db_path) を提供: 親ディレクトリ自動作成、全 DDL を実行して接続を返す。get_connection は既存 DB への接続を返す。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を実装し、実行結果（取得数・保存数・品質問題・エラー）を構造化して返す to_dict を提供。
  - 差分更新ヘルパー: テーブル存在確認、最大日付取得ユーティリティ（_table_exists / _get_max_date）、最終取得日の調整（_adjust_to_trading_day）を実装。
  - 差分 ETL ポリシー:
    - デフォルトの差分単位は営業日 1 日。
    - backfill_days を用いて最終取得日の数日前から再取得し、API の後出し修正を吸収する設計（デフォルト 3 日）。
    - run_prices_etl を部分実装（取得→保存→ログ）。（ファイル内に他ジョブのための骨格を用意）
  - 品質チェックフックを想定（quality モジュールと連携する設計。品質問題は致命的でも ETL を継続して報告する方針）。
- 型注釈とログ
  - 各モジュールに型注釈（PEP 484 互換）と詳細なログ出力（logger）を追加し、運用時のトラブルシュートを容易に。

Security
- RSS パーサに defusedxml を利用し XML の脆弱性を軽減。
- RSS フェッチで SSRF 対策を多数導入（スキーム制限、プライベートIP拒否、リダイレクト検査）。
- 外部データ取得で受信サイズ制限と gzip 解凍後サイズ検査を実施し、メモリ攻撃（DoS）対策を実装。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Notes / マイグレーション
- データ永続化には DuckDB を想定しているため、既存のデータベースがある場合は init_schema の適用方法に注意してください（init_schema は既存テーブルをスキップする設計）。
- .env 自動読み込みはデフォルトで有効です。テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制できます。
- 現時点で strategy、execution、monitoring パッケージは骨格（パッケージ初期化）を用意しているのみで、各実装は今後追加予定です。

Authors
- KabuSys 開発チーム（コードベースから推測して作成）