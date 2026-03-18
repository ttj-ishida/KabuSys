Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードから推測できる追加・設計方針・セキュリティ対策・既知の実装途上部分などを記載しています。必要なら日付やリリースノートの細部を編集してください。

Keep a Changelog
-----------------
すべての変更はセマンティックバージョニングに従います。  
詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
（次回リリースに向けた変更はここに記載）

0.1.0 - 2026-03-18
------------------
Added
- 初期リリース: KabuSys パッケージ（__version__ = 0.1.0）。
- パッケージ構成:
  - kabusys.config: .env / 環境変数の自動読み込みと設定管理を提供。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val、シングル/ダブルクォート、インラインコメントなどの .env 行解析に対応。
    - OS環境変数の上書きを保護する仕組み（protected set）。
    - Settings クラスで必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を定義。KABUSYS_ENV / LOG_LEVEL の検証、duckdb/sqlite のパス取得ユーティリティなどを提供。
- kabusys.data.jquants_client: J-Quants API クライアント機能を実装。
  - API 呼び出しのレート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx に対する再試行、429 の場合は Retry-After を優先。
  - 401 を検出した場合はリフレッシュトークンから id_token を自動で更新して1回だけ再試行（無限再帰防止）。
  - id_token のモジュールレベルキャッシュを保持しページネーション間で共有。
  - ページネーション対応のデータ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）で冪等性を確保（ON CONFLICT DO UPDATE）、fetched_at を UTC で記録。
  - 型変換ユーティリティ (_to_float, _to_int) により不正値に寛容な取り扱い。
- kabusys.data.news_collector: RSS ニュース収集機能を実装。
  - RSS フィードの取得とパース（defusedxml を利用して XML 攻撃対策）。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）、SHA-256（先頭32文字）で記事ID生成し冪等性を確保。
  - SSRF 対策:
    - fetch 前に URL スキーム検証（http/https のみ許可）。
    - リダイレクト先のスキームとホストを検査するカスタムハンドラ (_SSRFBlockRedirectHandler) を使用。
    - private/loopback/リンクローカル/マルチキャストなアドレスを拒否するチェック（IP 直接判定および DNS 解決による判定）。
    - DNS 解決失敗時は安全側の扱い（非プライベート）として通過させる設計（実運用では注意が必要）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入、gzip 解凍後のサイズ検査も実施して Gzip-bomb を回避。
  - テキスト前処理（URL除去、空白正規化）、銘柄コード抽出ロジック（4桁数字、known_codes でフィルタ）。
  - DB 保存はチャンク化してトランザクションで実行。INSERT ... RETURNING により実際に挿入された件数/ID を取得（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - run_news_collection により複数ソースの収集を統合、各ソースの失敗は他ソースに影響させないフェイルセーフ実行。
- kabusys.data.schema: DuckDB 用スキーマと初期化関数を実装。
  - Raw / Processed / Feature / Execution 層に対応する多くのテーブル定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - インデックス定義（頻出クエリパターンを想定）。
  - init_schema(db_path) で親ディレクトリ作成・DDL 実行・インデックス作成を行い接続を返す。get_connection は既存 DB への接続を返す（初期化は行わない）。
- kabusys.data.pipeline: ETL パイプライン基盤を実装。
  - ETLResult データクラス（取得・保存件数、品質チェック結果、エラーリスト等）と to_dict()。
  - テーブル最終日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - _adjust_to_trading_day による非営業日調整ロジック（market_calendar がある場合に過去の直近営業日に調整）。
  - run_prices_etl (株価差分 ETL): DB の最終取得日から backfill_days を考慮して差分取得し、jquants_client を使って取得・保存するロジックの実装（差分更新・バックフィルを想定）。
- ログ出力を各処理に追加し、実行状況や警告（例: PK 欠損スキップ、XML パース失敗、ネットワーク/HTTP 再試行等）を明示。

Security
- RSS パーシングに defusedxml を採用し XML 関連の脆弱性に対策。
- SSRF 対策を複数層で実装（スキームチェック、リダイレクト検査、プライベートIP拒否）。
- レスポンス受信サイズ制限と gzip 解凍後サイズチェックによる DoS 対策。
- .env 読み込みはプロジェクトルート検出による安全なスコープ制御、既存 OS 環境変数の保護機能を提供。

Notes / Known limitations
- strategy/ と execution/ の __init__.py は存在するが、具体的な戦略実装や発注処理はこのリリースで含まれていない（今後実装予定）。
- run_prices_etl の末尾がソース上で途中の記述に見える（return の取り扱いなど）。パイプライン周辺は追加実装・単体テストでの検証が想定される。
- _is_private_host は DNS 解決に失敗した場合に「非プライベート」とみなして通す実装になっている点は運用ポリシーによって再検討の余地あり。
- RSS の guid を URL として扱う場合、必ずしも URL でない guid が存在するため、その場合はスキップするロジックを採用している（仕様上の妥当性判断が必要なケースあり）。

Developer notes
- 環境変数の自動読み込みをテスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client の _request は urllib を直接使用しており、テスト時は urllib のモックまたは get_id_token などの id_token 注入を利用して外部依存を切り離すことが可能です。
- news_collector._urlopen はテスト用に差し替え可能（モックしやすい設計）。

ありがとうございました。必要であれば別ファイル（リリースノート英語版、または個々のモジュール向けの詳細な変更点）も作成します。