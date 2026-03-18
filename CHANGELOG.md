CHANGELOG
=========
このファイルは Keep a Changelog の形式に従って作成されています。
変更履歴は意図的に「注目に値する変更」を記載しています。

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース: KabuSys v0.1.0
- パッケージ構成を追加
  - モジュール: kabusys.config, kabusys.data, kabusys.data.jquants_client, kabusys.data.news_collector, kabusys.data.schema, kabusys.data.pipeline, など。
  - パッケージの __version__ を 0.1.0 として定義。
- 環境設定管理
  - .env ファイルまたは環境変数から設定値を自動読み込み（プロジェクトルート判定: .git / pyproject.toml）。  
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装: export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理に対応。
  - Settings クラスでアプリ設定をプロパティ経由で取得。必須変数は未設定時に ValueError を送出。KABUSYS_ENV と LOG_LEVEL の値検証を実装。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制限制御（_RateLimiter）: 120 req/min を固定間隔スロットリングで順守。
  - 再試行ロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx 対象）。
  - 401 受信時にリフレッシュトークンで自動的に ID トークンをリフレッシュして 1 回リトライ。
  - ID トークンのモジュールキャッシュを用意し、ページネーション間で共有。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）: ON CONFLICT DO UPDATE による冪等保存。
  - JSON デコード失敗時の明示的エラーハンドリング、タイムアウト・ログ出力等。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得と記事整形機能を実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
  - セキュリティ対策: defusedxml を使った安全な XML パース、SSRF 対策（ホストのプライベートアドレス判定、リダイレクト時の検証を行う専用 HTTPRedirectHandler）。
  - URL 正規化機能: トラッキングパラメータ除去（utm_*, fbclid 等）、スキーム/ホスト小文字化、フラグメント除去、クエリソート。
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査、Content-Length の事前チェック。
  - DB 保存はチャンク化（最大チャンクサイズ 1000）してトランザクションで実行。INSERT ... RETURNING を用いて実際に挿入された件数を返す実装。
  - テキスト前処理（URL 除去、空白正規化）および記事中からの銘柄コード抽出（4桁数字かつ known_codes に存在するもののみ）。
- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
  - 典型的クエリ向けインデックスを作成。
  - init_schema(db_path) によりディレクトリ自動作成＆スキーマ初期化（冪等）、get_connection() を提供。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass による実行結果表現（取得件数、保存件数、品質問題、エラー一覧）。
  - 差分更新ロジック: 最終取得日を基に自動で date_from を計算（backfill_days による後出し修正吸収）。
  - 市場カレンダー先読み（デフォルト 90 日）、最小データ日付の定義（2017-01-01）。
  - 品質チェック（quality モジュール連携）を行う設計（重大度を保持しつつ ETL は継続する方針）。
- ユーティリティ
  - 型変換ユーティリティ (_to_float / _to_int) を実装。空値・不正値を安全に None として扱う。float 文字列からの int 変換時は小数部がある場合は None を返す（意図しない切り捨て防止）。

Security
- RSS/XML 処理で defusedxml を採用し XML Bomb 等を防御。
- SSRF 対策を多層で実装:
  - URL スキーム検証（http/https のみ許可）。
  - ホストがプライベート/ループバック/リンクローカル/マルチキャストであればアクセスを拒否（IP 直解析 + DNS 解決で A/AAAA を検査）。
  - リダイレクト先検証用ハンドラを設け、接続前にスキームとホストをチェック。
- .env 自動読み込み時に OS 環境変数を保護（読み込み順と protected set による上書き制御）。

Performance
- API 呼び出しでレート制限（スロットリング）を導入し、レート違反による 429 リスクを低減。
- J-Quants クライアントはページネーションを透過的に扱う。
- DB 保存はバルク実行 / チャンク化 / トランザクションでオーバーヘッドを最小化。
- news_collector の記事・シンボル保存は INSERT ... RETURNING とチャンク化で実行数を削減。

Notes / Design Decisions
- ETL の品質チェックは「検出して報告しつつ ETL 自体は継続する」方針（呼び出し元がアクションを決定）。
- DuckDB スキーマは外部キー依存を考慮した順序で作成され、init_schema は冪等性を重視。
- ID トークンの自動リフレッシュは 401→1 回のリトライまで許容（無限再帰防止のため allow_refresh フラグを利用）。
- news_collector は記事 ID の衝突を避けるため URL の正規化を重視（UTM 等のトラッキングパラメータを削除）。

Fixed
- （初回リリースのため「Fixed」項目はありません）

Changed / Deprecated / Removed
- （初回リリースのため該当なし）

Acknowledgements / References
- 内部設計は DataPlatform.md / DataSchema.md の方針に基づく箇所があります（実装コメント参照）。

今後の予定（未リリース機能例）
- ETL の完全な品質チェック実装（quality モジュールとの連携詳細）
- strategy / execution モジュールの実装（戦略生成・発注ロジックの追加）
- モニタリング・Slack 通知など運用周りの強化

----- 

注: 本 CHANGELOG はリポジトリ内のコードと docstring コメントから推測して作成しています。実際のリリースノートとして公開する際は、担当者による確認・加筆を推奨します。