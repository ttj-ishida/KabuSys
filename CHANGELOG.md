Keep a Changelog
=================

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

[0.1.0] - 2026-03-17
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアモジュール群を追加。
- パッケージ初期化:
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - サブパッケージをエクスポート: data, strategy, execution, monitoring。
- 環境・設定管理 (src/kabusys/config.py):
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装（プロジェクトルート判定: .git / pyproject.toml）。
  - .env パーサーで export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントを取り扱い。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供。環境値のバリデーション（有効値チェック）を実装。
- J-Quants クライアント (src/kabusys/data/jquants_client.py):
  - API 呼び出しユーティリティを実装。レート制限（120 req/min）のための固定間隔 RateLimiter を搭載。
  - 冪等性を考慮したリトライロジック（指数バックオフ、最大再試行 3 回、408/429/5xx のリトライ、429 の Retry-After 優先）。
  - 401 受信時の自動トークンリフレッシュ（1 回だけ）とモジュールレベルの id_token キャッシュ。
  - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存、fetched_at に UTC タイムスタンプを記録。
  - 入出力変換ユーティリティ: _to_float, _to_int（空値/不正値の扱いと float→int の明確化）。
- ニュース収集 (src/kabusys/data/news_collector.py):
  - RSS フィード取得・前処理・DB 保存の包括的実装。
  - セキュリティ対策: defusedxml による XML パース防護、SSRF 対策（スキーム検証、プライベート/ループバック/リンクローカル判定、リダイレクト時検査）、HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）の削除、スキーム/ホストの小文字化、フラグメント除去、クエリソート。
  - 記事ID生成: 正規化 URL の SHA-256（先頭32文字）で冪等性を保証。
  - テキスト前処理（URL 除去・空白正規化）と pubDate → UTC naive datetime 変換。
  - DuckDB へのバルク保存: save_raw_news（チャンク分割、INSERT ... RETURNING を使用して新規挿入 ID を取得）、save_news_symbols、内部バルク関数 _save_news_symbols_bulk。いずれもトランザクション管理とエラーロールバックを実装。
  - 銘柄コード抽出関数 extract_stock_codes（4桁数字パターン + known_codes フィルタ）。
  - 全体収集ジョブ run_news_collection（各ソース独立エラーハンドリング、既知銘柄紐付け）。
- DuckDB スキーマ定義 (src/kabusys/data/schema.py):
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義。主キー・制約（CHECK）・外部キーを含む。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ作成 → テーブル・インデックス作成を行い接続を返す。get_connection() で既存 DB に接続可能。
- ETL パイプライン (src/kabusys/data/pipeline.py):
  - 差分更新方針に基づく ETL 実装骨子を追加。
  - ETLResult dataclass により ETL 実行結果（フェッチ数、保存数、品質問題、エラー等）を構造化して返却可能。
  - テーブル存在チェック、最大日付取得、営業日調整（market_calendar に基づく調整）などの補助関数を実装。
  - run_prices_etl（株価差分 ETL）の実装: 最終取得日の差分計算、backfill_days による再取得、J-Quants からの取得→保存フローを実装。デフォルトのバックフィル: 3 日。市場カレンダー先読み等の設計方針を考慮。
- 型注釈と静的解析対応:
  - PEP 484/PEP 526 スタイルの型ヒントを広く導入し、可読性とテスト容易性を向上。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサーに defusedxml を利用し XML 関連の脆弱性に対処。
- HTTP フェッチ時に SSRF 対策を実施（スキーム検証、プライベートIP/ホストの判定、リダイレクト時の検査）。
- 外部からの不正な URL スキーム（file:, javascript:, mailto: 等）を拒否。
- レスポンスサイズと gzip 解凍後サイズの制限によりメモリ DoS や圧縮爆弾を防止。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Known issues
- run_prices_etl の返り値は設計上 (fetched_count, saved_count) のタプルを返すことになっているが、実装の一部（リストの末尾）に不完全な返却処理や実装継続箇所が見受けられます。実運用前に戻り値の整合性（両要素の確実な返却）とその他 ETL ジョブの単体テストを推奨します。
- 初期リリースのため、運用時のエッジケース（大量データ取得時のパフォーマンス、長期運用におけるトークン更新の挙動等）は実運用での観測に基づく改善が想定されます。
- schema の DDL は厳格な型・制約を含みます。既存データ移行や他システムからの利用時は互換性確認が必要です。

Authors
- 実装（コードの内容から推測）: KabuSys 開発チーム相当

Acknowledgements
- J-Quants, kabuステーション API を利用したデータ取得ロジックに対応。RSS 処理に defusedxml を採用。

---