# Changelog

すべての注目に値する変更はこのファイルに記載します。
このプロジェクトは Keep a Changelog の慣習に従います。
変更履歴のフォーマットは semver に従っています。

## [0.1.0] - 2026-03-18

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネント群を追加。
  - パッケージ情報
    - src/kabusys/__init__.py にパッケージ名・バージョン（0.1.0）と公開モジュール一覧を定義。
  - 設定管理
    - src/kabusys/config.py
      - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
      - 自動 .env ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
      - ロード優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化機能を提供（テスト時に利用可能）。
      - export KEY=val 形式やクォート付き値、行内コメントの扱い等に対応した .env パーサを実装。
      - 必須変数取得用の _require と環境値チェック（KABUSYS_ENV, LOG_LEVEL）を実装。
      - データベースパス（DuckDB / SQLite）、Slack, kabu API, J-Quants など主要設定のプロパティを提供。
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* API を提供。
      - ページネーションに対応（pagination_key を用いたループ取得）。
      - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
      - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータス（408, 429, 5xx）に対するリトライ。
      - 401 受信時はリフレッシュトークンを用いて id_token を自動リフレッシュし1回だけ再試行。
      - id_token キャッシュ（モジュールレベル）を実装し、ページネーション間で共有。
      - DuckDB への保存用関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（冪等性: ON CONFLICT DO UPDATE）。
      - 値変換ユーティリティ (_to_float, _to_int) を実装し入力の堅牢性を向上。
  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィードから記事を収集し raw_news に保存する fetch_rss / save_raw_news 等を実装。
      - セキュリティと堅牢性:
        - defusedxml を用いた XML パースで XML Bomb 等に対処。
        - リダイレクト時にスキームとホスト/IP を検査する _SSRFBlockRedirectHandler を実装し SSRF を防止。
        - レスポンス最大サイズ（MAX_RESPONSE_BYTES = 10MB）で受信を制限、gzip 解凍後もサイズチェック。
        - http/https スキームのみ許可、プライベートアドレスへのアクセスを拒否。
      - 記事 ID は正規化した URL の SHA-256 を用いて生成（先頭32文字）することで冪等性を確保。
      - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）除去、クエリをソート、フラグメント削除。
      - テキスト前処理 (URL 除去、空白正規化) を実装。
      - DB 書き込み: チャンク挿入、トランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入された ID を返す実装。
      - news_symbols への銘柄紐付け保存（単件・バルク）を実装（ON CONFLICT DO NOTHING、RETURNING 利用）。
      - 銘柄コード抽出ユーティリティ (4桁数字パターン) を実装し既知コードセットでフィルタ。
      - テスト容易性のため _urlopen を差し替え可能（モック可能）。
  - DuckDB スキーマ定義
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を実装。
      - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed Layer。
      - features, ai_scores の Feature Layer。
      - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution Layer。
      - 各種インデックス（頻出クエリの最適化）を作成。
      - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等的にテーブル/インデックス作成）と get_connection を提供。
  - ETL パイプライン
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass による ETL 実行結果の集約（品質問題・エラー集計を含む）。
      - 差分更新ロジック（最終取得日を基に date_from を自動算出、backfill_days による再取得）を実装。
      - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS=90）など ETL の設計方針を反映。
      - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパー。
      - run_prices_etl: 差分取得・保存のワークフロー（backfill デフォルト 3 日、最小データ日付 2017-01-01）を実装（fetch -> save の呼び出しに対応）。
  - その他
    - モジュールレベルでのログ出力を多用し、処理の可観測性を向上。
    - SQL 実行のプレースホルダ使用や chunk 分割によりパフォーマンス・安全性を考慮。

### Security
- ニュース収集における SSRF 対策、defusedxml による XML 攻撃対策、受信バイト数制限など複数の安全対策を導入。
- .env の読み込みは既存 OS 環境変数を保護する設計（protected set を用いた上書き制御）。

### Known Issues / Notes
- ETL パイプライン内の run_prices_etl の末尾の return 文が不完全（現在の配布コード断片では "return len(records), " のようにタプルが未完了）になっている箇所が確認されます。このままでは構文エラーや実行時エラーが発生する可能性があります。実運用前に return 値・呼び出し側との整合性を確認・修正してください。
- いくつかの ETL 関数は設計文書（DataPlatform.md 等）に沿った実装方針がコード内に反映されていますが、実運用前に動作確認（API 実行・大規模データの保存・バックフィル挙動）と追加のエラーハンドリング・監視の整備を推奨します。
- データ保存の検証（スキーマとの整合性、NULL/チェック制約違反に対する堅牢な動作）のための単体・統合テストの整備を推奨。

---

注: 本 CHANGELOG は提供されたコード内容から推測して作成しています。実際のリリースノートとして使用する場合は、リリース時のコミット・変更点・既知のバグを改めて確認のうえ補正してください。