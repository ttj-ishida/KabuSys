# Changelog

すべての注記は「Keep a Changelog」仕様に準拠しています。  
このファイルは変更履歴（機能追加・修正・既知の制約など）を人間向けに要約したものです。

現在の最新バージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
最初の公開リリース。日本株自動売買システムの基盤となる以下の主要機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - モジュール構成のスケルトン: data, strategy, execution, monitoring。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を自動読み込みする仕組みを実装。
  - 自動読み込みの探索はパッケージファイル位置を起点にプロジェクトルート（.git または pyproject.toml）を探索し決定するため、CWD に依存しない設計。
  - .env と .env.local の優先度、既存 OS 環境変数の保護（protected set）や override フラグに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化オプションをサポート（テスト用想定）。
  - 必須設定の取得関数（_require）と Settings クラスを提供。以下の主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - 環境判定ヘルパー is_live/is_paper/is_dev

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
  - リトライロジック: 指数バックオフ、最大 3 回。408/429/5xx を再試行対象。
  - 401 応答時はリフレッシュトークンから id_token を自動リフレッシュして 1 回再試行（再帰回避のため allow_refresh フラグ制御）。
  - ページネーション対応（pagination_key を用いた続次取得）。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias のトレーサビリティを確保。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等保存を保証。
  - 型変換ユーティリティ (_to_float, _to_int) により不正値に対する寛容な扱いを実装。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news テーブルへ保存する処理を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML 関連攻撃を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定、リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）、DNS 解決時の内部アドレス検出。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 許可されていないスキームやプライベートホストの場合はフェッチを拒否。
  - 記事IDは正規化した URL の SHA-256（先頭32文字）で生成して冪等性を担保（utm_* 等のトラッキングパラメータを除去）。
  - コンテンツの前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を用い、実際に挿入された記事IDのみを返す（チャンク処理、トランザクション単位でコミット/ロールバック）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（重複除去、ON CONFLICT DO NOTHING、INSERT ... RETURNING により挿入数を正確に算出）。
  - 銘柄抽出ロジック: 4桁数字パターンを検出し、既知の銘柄セットと照合して重複除去して返す（extract_stock_codes）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform.md に基づいた3層（Raw / Processed / Feature）+ Execution 層のテーブル群を定義。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - プライマリキー・チェック制約・外部キー等を適切に設定。
  - パフォーマンス用インデックス群を作成（コード・日付検索やステータス検索を高速化）。
  - init_schema(db_path) で必要な親ディレクトリを自動作成して全 DDL を実行（冪等）。get_connection() を用いた接続取得 API も提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を前提とした ETL 処理の基盤を実装:
    - DB 側の最終取得日から差分（＋backfill_days）を自動計算して差分取得を行う設計。
    - run_prices_etl を含む個別 ETL ジョブ基盤（価格、財務、カレンダー等へ適用予定）。
  - ETLResult データクラスを追加して ETL 実行結果（取得数、保存数、品質問題、エラー）を収集・表現。
  - スキーマ存在チェック、最大日付取得、営業日調整（market_calendar を参照して非営業日を直近営業日に調整）等のユーティリティを実装。
  - デフォルトのバックフィル日数: 3 日（後出し修正吸収用）。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）等の設計方針を反映。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し、かつ SSRF 対策（スキーム制限、プライベートアドレス検出、リダイレクト時の検査）を施しました。
- HTTP レスポンスサイズ・gzip 解凍後サイズの上限を設け、リソース枯渇攻撃を緩和しています。

### 既知の制約 / 注意点 (Known issues / Notes)
- jquants_client の _request は urllib を用いた同期実装であり、大量並列リクエストを行う用途には RateLimiter に基づくスロットリングが必要です。非同期 I/O のサポートは現状含まれていません。
- ETL の品質チェックモジュール（quality）は参照されているが、このリリース内での具体実装の詳細は別途（外部モジュール/今後の実装）を想定しています。
- settings._require は未設定の必須環境変数で ValueError を送出します。CI / 実行環境での .env 設定確認を推奨します。
- news_collector の DNS 解決が失敗した場合は安全側に寄せ（非プライベートと扱う）ため、特殊な DNS 環境では挙動差分が生じる可能性があります。

### 互換性 (Compatibility)
- 初回リリースのため後方互換問題はありません。将来的にテーブル定義・カラム名変更が発生する場合はマイグレーション方針を追って案内します。

---

今後の予定（例）
- ETL の完全なスケジューリング・品質チェック実装（quality モジュールの実装拡充）。
- strategy / execution / monitoring モジュールの実装（発注ロジック、kabu API 連携、監視・アラート機能）。
- 非同期処理・並列性向上、テストカバレッジ拡張。

上記内容で不明な点や、特に詳細を追記してほしい箇所があれば教えてください。