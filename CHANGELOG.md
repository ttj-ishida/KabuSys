# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

## [Unreleased]
- 今後のリリース向けに未確定の改善・追加をここに記載します。

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### 追加
- パッケージ基礎
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。
  - モジュール群のエントリ（data, strategy, execution, monitoring）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの自動設定ロード機能を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env の行パーサ（export 対応、クォート/エスケープ対応、インラインコメント処理）。
  - Settings クラスによる環境変数のラップ:
    - 必須設定の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値（KABUSYS_ENV の default: development、KABU_API_BASE_URL 等）。
    - env / log_level の値検証（許容値チェック）。
    - パス設定を pathlib.Path で返す（duckdb/sqliteパス）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得関数を実装（ページネーション対応）。
  - レート制限制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、対象ステータス: 408, 429, 5xx）。
  - 401 応答時の自動トークンリフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ。
  - JSON デコード失敗時の明確なエラー報告。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。いずれも冪等（ON CONFLICT ... DO UPDATE）で保存。
  - レコード保存時に fetched_at を UTC で記録して Look-ahead bias を防止。
  - ユーティリティ関数: _to_float / _to_int（空値や不正値を安全に変換）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得・前処理・DB保存するフローを実装。
  - 設計上の特徴:
    - 記事ID は正規化後の URL の SHA-256 の先頭32文字で生成（utm_* 等トラッキング削除）。
    - defusedxml を利用した安全な XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないか検査、リダイレクト時も検査するカスタム RedirectHandler。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後のサイズ再検査（Gzip bomb 対策）。
    - 取得記事のテキスト前処理（URL除去、空白正規化）。
    - DB 保存はチャンク化してトランザクションでまとめて実行、INSERT ... RETURNING で実際に挿入された記事IDを返却。
    - 銘柄コード抽出（4桁数字パターン）と news_symbols への紐付けを一括保存する関数を提供。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録。

- スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）をDDLで実装。
  - 主要クエリ向けのインデックス定義を追加。
  - init_schema(db_path) でディレクトリ作成 → 接続 → テーブル作成（冪等）を実行。get_connection() も提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 処理の設計方針に沿ったヘルパー群と一部実装:
    - ETLResult dataclass（品質チェックやエラー集約、辞書化メソッドを含む）。
    - テーブル存在チェック、最大日付取得ユーティリティ。
    - market_calendar に基づく営業日調整ヘルパー。
    - 差分更新ヘルパー関数（get_last_price_date 等）。
    - run_prices_etl の骨組み（差分算出、backfill_days による再取得、fetch → save の流れ）を実装（部分的に続きあり）。

### セキュリティ関連
- defusedxml を使用して XML パース／外部実行攻撃を回避。
- ニュース収集での SSRF 対策を強化（スキーム/ホスト検査、リダイレクト時検査）。
- RSS レスポンスサイズ上限を設け、メモリDoSや Gzip bomb を防止。

### 修正（設計上の注記・改善）
- .env パーサはシェル風の export 構文、クォート・エスケープ、インラインコメントを考慮するよう改善。
- J-Quants クライアントはトークンリフレッシュループを回避するため allow_refresh フラグを導入。

### 既知の制限 / 注意点
- ETL パイプラインは基本的な機能を提供しますが、完全なジョブ制御（スケジューラ統合、詳細な品質チェックルールの適用等）は今後の拡張対象です。
- news_collector の DNS 解決失敗時は安全側の挙動（非プライベート扱い）としており、特殊ケースの処理は運用での監視が必要です。
- jquants_client のエラーメッセージはネットワーク/HTTP レイヤに依存するため、運用時はログレベル設定と併せて監視してください。

### 開発者向けメモ
- 環境変数の必須チェックに失敗すると ValueError を発生させます。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD やテスト用の環境変数注入を利用してください。
- news_collector の _urlopen はテスト時にモック差し替え可能です（モジュールレベルで置換して使用）。

---

今後のリリースでは、ETL の完全実装、品質チェックモジュールの詳細実装、strategy / execution / monitoring の具体的なロジック実装およびテストカバレッジ強化を予定しています。