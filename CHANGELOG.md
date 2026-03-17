# CHANGELOG

すべての変更は Keep a Changelog の規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本リポジトリは初回リリースとしてバージョン 0.1.0 を公開します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システムの基盤機能を実装しました（データ取得・保存、RSS ニュース収集、設定管理、DuckDB スキーマ、ETL パイプラインの基礎など）。

### Added
- パッケージのエントリポイントを追加
  - src/kabusys/__init__.py にバージョン情報（0.1.0）と公開モジュール一覧を定義。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルの堅牢なパース実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等をサポート）。
  - OS 環境変数を保護する protected ロジック（.env.local が OS 環境変数を上書きしないように）。
  - 必須環境変数取得ヘルパー _require。
  - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack 設定、DB パス、環境/ログレベル検証、is_live/is_paper/is_dev 等の利便性プロパティ）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - API ベースURL、レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）。429 の場合は Retry-After を優先。
  - 401 応答時に refresh_token を用いた id_token 自動リフレッシュを1回だけ行う仕組み。
  - ページネーション対応のデータフェッチ関数:
    - fetch_daily_quotes（株価日足：OHLCV）
    - fetch_financial_statements（財務データ：四半期 BS/PL）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ（_to_float, _to_int）。_to_int は小数部が存在する場合は変換を回避する等の安全設計。
  - fetched_at に UTC タイムスタンプを記録し、Look-ahead Bias 対策を考慮。

- RSS ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を取得して raw_news に保存する機能。
  - セキュリティ指向の設計:
    - defusedxml を用いた XML パース（XML Bomb などに配慮）。
    - SSRF 対策（URL スキーム検証、リダイレクト先のスキーム・ホスト事前検査、プライベートIP/ループバック判定）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - HTTP レスポンスの Content-Length 事前チェックと実際の読み取り上限。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）、記事ID を正規化 URL の SHA-256（先頭32文字）で算出して冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄コード抽出ユーティリティ（4桁数値を検出し known_codes によりフィルタ）。
  - DB 保存:
    - save_raw_news: チャンク処理、トランザクション、INSERT ... RETURNING を使って新規挿入IDを返却。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの一括紐付け保存（ON CONFLICT DO NOTHING、チャンク化、トランザクション）。
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3層（Raw / Processed / Feature / Execution）に対応するテーブル群を定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を設定。
  - 検索を意識したインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) により親ディレクトリ作成を含めてスキーマを冪等に初期化するユーティリティを提供。
  - get_connection(db_path) を提供（既存 DB への接続用）。

- ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py）
  - ETLResult dataclass により ETL 実行結果（取得数、保存数、品質問題、エラーなど）を構造化して返却。
  - DB の最終取得日を取得するヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを参照して営業日に調整する _adjust_to_trading_day。
  - 差分更新用ロジックと run_prices_etl の実装（差分算出、backfill_days による後出し修正吸収、jquants_client を使った取得と保存）。
  - ETL の設計方針（差分更新デフォルト、品質チェックは集約して報告する等）をコードコメントで明示。

- 空ファイルのパッケージ化プレースホルダ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を追加（将来的な実装のためのプレースホルダ）。

### Changed
- 初回公開のため特になし（すべて新規追加）。

### Fixed
- 初回公開のため特になし。

### Security
- news_collector における複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキーム検査、プライベートホスト判定、リダイレクト検査）。
  - レスポンスサイズ上限と gzip 解凍後チェックによる DoS 対策。

### Notes / Known limitations
- strategy、execution パッケージは初期プレースホルダのみで、実際の戦略ロジックや発注実行ロジックは未実装です。
- ETL やクライアントの単体テスト・統合テストは別途用意が必要です（モック可能なフックは一部用意されています）。
- run_prices_etl 等の ETL 関数は差分ロジックを実装していますが、品質チェックモジュール (kabusys.data.quality) の実装・統合は別途必要です。
- .env パースは多くのケースをサポートしますが、特殊な .env フォーマットに対する追加の検証が必要な場合があります。

---

（今後のリリースでは、strategy/ execution の実装、監視/通知機能の統合、品質チェックの本格実装、テストカバレッジ拡充などを予定しています。）