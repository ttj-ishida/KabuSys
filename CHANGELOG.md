Keep a Changelog の形式に準拠した CHANGELOG.md を以下に作成しました。初回リリース v0.1.0（2026-03-17想定）として、コードベースから推測される追加機能・設計方針・注意点を記載しています。必要に応じて日付や項目の詳細を調整してください。

# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]


## [0.1.0] - 2026-03-17

Added
- パッケージ初版: kabusys（日本株自動売買システム）の基本モジュール群を追加
  - パッケージトップ: src/kabusys/__init__.py（バージョン 0.1.0、公開サブパッケージ設定）
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルートから自動読み込みする機能を追加（優先度: OS環境変数 > .env.local > .env）。
  - プロジェクトルートは .git や pyproject.toml を基準に探索するため CWD に依存しない実装。
  - 行パーサは export プレフィックスやシングル/ダブルクォート、インラインコメント、エスケープを考慮している。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等をプロパティ経由で取得。
  - 必須環境変数が未設定の場合は ValueError を送出する _require を実装。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API レート制御: 固定間隔スロットリングにより 120 req/min を遵守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータス（408, 429, 5xx）に対応。429 の場合は Retry-After ヘッダ優先。
  - 認証: refresh_token から id_token を取得する get_id_token とモジュールレベルの id_token キャッシュ、401 発生時の自動1回リフレッシュ対応。
  - ページネーション対応（pagination_key を利用して全ページ取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。fetched_at を UTC ISO8601（Z）で記録し、INSERT は ON CONFLICT DO UPDATE で冪等性を確保。
  - 値変換ユーティリティ (_to_float, _to_int) を備え、不正な数値や空値は None に変換する安全設計。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存、銘柄紐付けを行う一連の実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - デフォルト RSS ソース（Yahoo Finance）を定義。
  - セキュリティ対策: defusedxml を用いた XML パース、防止策付きリダイレクトハンドラでの SSRF 対策（スキーム検証、プライベートホスト検出）、受信バイト数上限（10 MB）や gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_ 系、fbclid 等）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - コンテンツ前処理（URL除去、空白正規化）と RFC 2822 形式 pubDate の安全なパース（タイムゾーン処理）。
  - DB 挿入はチャンク（デフォルト 1000 件）でまとめてトランザクション処理。INSERT ... RETURNING を用いて実際に挿入された件数/ID を正確に取得。
  - 銘柄コード抽出ユーティリティ（4桁数字パターンに基づく、既知コードセットによるフィルタ）。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層（＋実行層）に対応するテーブル群を DDL で定義。
  - raw_prices, raw_financials, raw_news, raw_executions、prices_daily, market_calendar, fundamentals, news_articles, news_symbols、features, ai_scores、signals, signal_queue, orders, trades, positions, portfolio_performance などを定義。
  - 適切な型制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を設置し、外部キー依存を考慮した作成順序を保持。
  - インデックス定義（頻出クエリに対する index）を実装。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行・インデックス作成まで実施。get_connection は既存 DB への単純接続を提供。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新とバックフィル（デフォルト backfill_days=3）を考慮した ETL ヘルパ群を実装。
  - ETLResult データクラスを提供し、取得件数・保存件数・品質問題・エラー情報を集約。品質問題は辞書化して出力可能。
  - テーブル存在確認・最終取得日の取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 取引日調整ヘルパ (_adjust_to_trading_day) を実装（market_calendar がない場合のフォールバックあり）。
  - run_prices_etl の差分取得ロジックを実装（date_from 自動算出、最小取得日 2017-01-01 を使用、fetch と save の呼び出し）。

Security
- ニュース収集での SSRF 対策を実装
  - URL スキーム検証（http/https のみ許可）
  - リダイレクト時のスキーム・ホスト検査（プライベートアドレス拒否）
  - defusedxml を利用して XML 関連攻撃を緩和
  - レスポンスサイズ上限・gzip 解凍後のサイズ検査でメモリ DoS を緩和
- 環境変数ロードで OS 環境変数を保護する protected キー概念を導入し、.env/.env.local の上書き制御を実装

Performance
- J-Quants API クライアントで固定間隔スロットリングによりレート制限遵守（120 req/min）
- RSS/News 保存でチャンク化（_INSERT_CHUNK_SIZE）とトランザクションまとめ書きにより挿入オーバーヘッドを削減
- DuckDB 側で ON CONFLICT DO UPDATE（または DO NOTHING）により冪等な保存を実現

Notes / 設計上の注意
- settings は環境変数が未設定の場合に例外を投げるため、CI/運用で必須環境変数を適切に設定する必要がある。
- get_id_token は refresh_token を settings から取得するが、allow_refresh=False の呼び出しパスでは自動リフレッシュを無効化している（無限再帰対策）。
- pipeline.run_prices_etl はファイルの途中まで実装されたように見える（リターンのタプルの書き方が途中で終わっている等）。（レビュー・補完が必要）
- ニュース記事の ID は URL 正規化後のハッシュを使用するため、同一記事の URL 変化（トラッキングパラメータのみの違い）は正しく重複排除される設計。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

---

（補足）
- 実装中の箇所や補完が必要な点（例えば pipeline.run_prices_etl の戻り値のタプル処理など）はコードコメントや TODO として追記してください。必要であれば変更履歴の「Unreleased」へ追加で記載します。