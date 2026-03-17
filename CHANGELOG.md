# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買プラットフォームのコア機能を実装しました。主に以下の機能・設計を含みます。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期化（__version__ = 0.1.0、公開モジュール一覧を定義）。 (src/kabusys/__init__.py)

- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。必須値に対する取得ヘルパーを提供（_require）。(src/kabusys/config.py)
  - 自動 .env ロード機能を導入（プロジェクトルートは .git または pyproject.toml を基準に特定）。.env → .env.local の順で読み込み、.env.local は上書きを許可。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント行、export プレフィックス、クォート内エスケープ、行内コメントの扱い等に対応）。

- J-Quants API クライアント
  - J-Quants から日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装。(src/kabusys/data/jquants_client.py)
  - レート制限制御（固定間隔スロットリング: 120 req/min）を実装する RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）を実装。429 の場合は Retry-After を優先。
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して1回だけリトライする仕組みを実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を用い、fetched_at を UTC で記録して Look-ahead Bias を抑制。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正入力に対して安全に None を返す。

- ニュース収集 (News Collector)
  - RSS フィードから記事を取得し raw_news に保存するモジュールを実装。記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。(src/kabusys/data/news_collector.py)
  - トラッキングパラメータ（utm_* 等）の除去、URL 正規化、fragment 削除、クエリソートなどの正規化処理を実装。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先を事前検証するカスタム RedirectHandler（プライベート/ループバック/リンクローカル/マルチキャストアドレスへのアクセスを拒否）。
    - ホスト名の DNS 解決結果も検査してプライベートIPを弾くロジック。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、大きすぎるレスポンスを拒否。gzip 解凍後もサイズチェック。
  - 取得した記事をチャンク化して DuckDB に INSERT ... ON CONFLICT DO NOTHING RETURNING id で保存し、実際に挿入された記事IDのみを返す（トランザクションでまとめて処理）。
  - news_symbols（記事と銘柄の紐付け）をバルクで保存する内部関数（重複除去・チャンク化・RETURNING）を提供。
  - テキスト前処理（URL 除去、空白正規化）と、本文からの銘柄コード抽出（4桁数字、known_codes フィルタ）を実装。
  - run_news_collection により複数 RSS ソースの統合収集ジョブを実装。ソース単位でエラー隔離して継続可能。

- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装し、init_schema で一括初期化できるようにした。複数の制約・チェック・外部キー・インデックスを含む。 (src/kabusys/data/schema.py)
  - 代表的テーブル: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions 等。
  - init_schema は親ディレクトリ自動作成、:memory: サポート、冪等にテーブル作成を行う。

- ETL パイプライン基盤
  - ETLResult データクラス（品質チェック結果・エラー記録を含む）を実装。to_dict により品質問題を簡易シリアライズ可能。(src/kabusys/data/pipeline.py)
  - 差分更新ユーティリティ（テーブル存在チェック、最大日付取得）を実装。market_calendar を参照して非営業日を直近営業日に調整するヘルパーを追加。
  - run_prices_etl の基礎（最終取得日の backfill ロジック、fetch → save の流れ）を実装。初期データの最小日付やデフォルト backfill 日数を定義。

### 変更 (Changed)
- 設計方針の明確化（ドキュメントコメント）
  - 各モジュールで設計原則（冪等性、Look-ahead 防止、RateLimit 遵守、トランザクション集約、エラー隔離等）を明文化。

### 修正 (Fixed)
- .env 読み込みでの既存 OS 環境変数保護（.env の上書きを制御する protected set を導入）。
- RSS パース時の不正スキームや不適切な guid/link をログ出力して安全にスキップするようにした。
- gzip/Content-Length の両チェックにより大きなレスポンスを検出してメモリ DoS を回避。

### セキュリティ (Security)
- defusedxml を採用して XML 脆弱性（XML External Entity / XML Bomb 等）から保護。
- SSRF 対策を多数実装:
  - URL スキーム制限（http/https のみ）
  - リダイレクト先のスキーム & ホスト検証
  - ホスト名の DNS 解決結果の IP 検査（プライベート・ループバック等を遮断）
- RSS レスポンスサイズ上限と gzip 解凍後の再チェックでメモリ DoS を軽減。

### 注意事項 (Notes)
- 環境変数の必須キー（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）が未設定の場合、Settings のプロパティアクセス時に ValueError を発生させます。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要があり、LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかでなければなりません。
- DuckDB スキーマの初期化は init_schema() を利用してください。既存 DB に接続するだけなら get_connection() を使用します。
- run_prices_etl 等の ETL 関数は id_token の注入可能性を持ち、テスト容易性を考慮しています。

---

今後のリリース予定（例）
- ETL の品質チェック実装（quality モジュールの具体的チェック適用）
- execution 層の外部 API（kabu ステーション連携）実装
- strategy レイヤーのサンプル戦略とモニタリング機能の追加

（以上）