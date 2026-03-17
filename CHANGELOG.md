CHANGELOG
=========
すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に従って記載しています。

Unreleased
----------
（現時点のコードから推測される今後の予定・既知の追加余地）
- ETL パイプラインの続き（prices, financials, calendar の完全実装・バックフィル制御・品質チェックの統合など）を継続。
- strategy / execution モジュールの実装（現在はパッケージのみ存在）。
- 単体テスト・統合テストの拡充（ネットワーク依存部分のモック化など）。
- モニタリング・アラート（Slack 通知等）の実装・強化。

0.1.0 - 2026-03-17
-----------------
初回リリース（コードベースの現状に基づく機能群の追加）

Added
- パッケージ基本情報
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ で public サブパッケージ（data, strategy, execution, monitoring）を宣言。

- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読込する仕組みを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準）。
  - .env 行パーサの実装（export 形式、クォート・エスケープ、インラインコメント対応）。
  - .env.local を .env より優先して上書きする挙動を実装。既存 OS 環境変数は保護。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。
  - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションを実装。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を導入。
  - 再試行（指数バックオフ）ロジックを実装（最大 3 回、408/429/5xx をリトライ対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回）およびモジュールレベルの id_token キャッシュを導入。
  - ページネーション対応で fetch_daily_quotes / fetch_financial_statements を実装。
  - 市場カレンダー取得用 fetch_market_calendar を実装。
  - DuckDB への冪等保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除・更新。
    - fetched_at に UTC タイムスタンプを付与して「いつ取得したか」をトレース可能に。
  - JSON デコード失敗や HTTP エラー時のエラーハンドリングを整備。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得する fetch_rss を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）。
    - HTTP(S) スキームの検証と SSRF 対策（プライベート IP/ループバック等への接続拒否）。
    - リダイレクト時に検査を行うカスタムリダイレクトハンドラを実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip の解凍後サイズチェックを導入。
  - URL 正規化（トラッキングパラメータ除去）と SHA-256 ハッシュから記事 ID 生成（先頭32文字）を実装し、冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）を提供。
  - DuckDB への保存:
    - save_raw_news: チャンク化して一括 INSERT、ON CONFLICT DO NOTHING を用い、実際に挿入された記事IDを返却。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存し、INSERT ... RETURNING で実際に挿入された件数を返却。
    - トランザクション管理（begin/commit/rollback）と例外時のロールバックを実装。
  - 銘柄コード抽出（extract_stock_codes）: 正規表現で4桁数字を抽出し、known_codes でフィルタして重複除去して返す。
  - run_news_collection: 複数 RSS ソースからの収集ジョブを実装。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema に基づく多層（Raw / Processed / Feature / Execution）テーブル定義を実装。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK 句, FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) を実装し、必要に応じて親ディレクトリを作成して全テーブル・インデックスを作成（冪等）。
  - get_connection(db_path) を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラーなど）を構造化して返却できるように実装。
  - 差分更新ヘルパー（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl を実装（差分算出、backfill_days 処理、J-Quants からの取得→保存のフロー）。
  - 設計上の方針（差分更新、backfill による後出し修正吸収、品質チェックの非 Fail-Fast 動作）をコードに反映。

Security
- 環境変数の取り扱いで OS 環境変数を保護する機構（.env の上書きを制御）。
- news_collector で SSRF 対策（プライベートホスト検出、スキーム検証、リダイレクト時検査）。
- defusedxml を採用して XML 関連の脆弱性に対処。
- ネットワーク・HTTP レスポンスサイズ上限および gzip 解凍後のサイズチェックによる DoS 対策。

Notes / Known limitations
- strategy/ execution / monitoring サブパッケージは存在するが実装がほとんどない（今後の実装予定）。
- pipeline.run_prices_etl は価格データの処理フローを実装しているが、financials / calendar の ETL 完全統合や品質チェックの呼び出しフローは今後の実装で拡張予定。
- 外部 API（J-Quants, RSS）呼び出しはネットワークに依存するため、テスト時はモック化が必要（コード中にモック差替え可能なフックあり）。

Contributing
- バグ修正・機能追加の際は、既存の DuckDB スキーマ・トランザクションの整合性に注意してください。
- ネットワーク関連処理のユニットテスト作成時は、モジュールレベルで用意された差替えポイント（例: news_collector._urlopen）を利用してください。

--------------------------------------------------------------------------------
（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成したものであり、実際のコミット履歴に基づくものではありません。