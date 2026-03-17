# Changelog

すべての重要な変更は Keep a Changelog の規約に従って記載します。  
このファイルは安定した API 変更履歴とリリースノートのために維持してください。

注: この CHANGELOG は提供されたコードベースから推測して作成しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回リリース — KabuSys: 日本株自動売買用データ基盤・ユーティリティ群

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。公開モジュール: `data`, `strategy`, `execution`, `monitoring` を想定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロードの優先順位: OS環境変数 > .env.local > .env。
    - テスト時などに自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - プロジェクトルート検出は `__file__` を起点に `.git` または `pyproject.toml` を探索して行うため CWD に依存しない。
  - .env パーサーの実装:
    - `export KEY=val` 形式、引用符付き値、インラインコメント（クォートなしでは直前が空白の場合に認識）に対応。
    - 読み込み時に OS 環境変数の上書きを制御する `override`、保護キーセット `protected` をサポート。
  - 設定ラッパー `Settings` を実装:
    - J-Quants / kabuステーション / Slack / DB（DuckDB/SQLite）等の設定プロパティを提供。
    - `env` / `log_level` の入力検証（許容値検査）。
    - ヘルパー: `is_live`, `is_paper`, `is_dev`。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - J-Quants から日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得する機能を実装。
  - レート制限対策: 固定間隔スロットリング（120 req/min の実装）。
  - リトライロジック: 指数バックオフによる最大 3 回リトライ（対象: 408/429/5xx）。429 の場合は Retry-After を尊重。
  - 401 Unauthorized を検出した場合のトークン自動リフレッシュ（1 回のみリトライ）。
  - ページネーション対応（pagination_key を用いた全件取得）。
  - データ保存関数（DuckDB 用）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`：いずれも冪等性を考慮し、ON CONFLICT (DO UPDATE) により重複を排除/更新。
    - 保存時に `fetched_at`（UTC）を記録し、いつデータを取得したかをトレース可能に。
  - 型安全なパースユーティリティ `_to_float`, `_to_int` を提供（不正値は None に変換）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュースを取得して `raw_news` テーブルへ保存するフローを実装。
  - セキュリティ・堅牢性機能:
    - defusedxml を用いた安全な XML パース（XML Bomb 等に対処）。
    - SSRF 対策: リダイレクト先のスキーム検証、プライベートアドレス（ループバック・リンクローカル・プライベート）検出を行い、内部アドレスへのアクセスを拒否。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）チェックと Gzip 解凍後の再チェック（Gzip Bomb 対策）。
    - カスタム HTTP リダイレクトハンドラ（_SSRFBlockRedirectHandler）と差し替え可能な `_urlopen`（テスト向けにモック可能）。
  - コンテンツ処理:
    - URL 除去・空白正規化を行う `preprocess_text`。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を保証（utm_* 等トラッキングパラメータを除去）。
    - pubDate の RFC2822 パース（タイムゾーン正規化、パース失敗時は代替時間を利用）。
  - DB 保存:
    - `save_raw_news` はチャンク INSERT（INSERT ... RETURNING）を用い、新規挿入された記事IDのみを返す（ON CONFLICT DO NOTHING）。
    - `save_news_symbols` / `_save_news_symbols_bulk` による記事と銘柄コードの紐付けをサポート（チャンク・トランザクション、ON CONFLICT DO NOTHING）。
  - 銘柄コード抽出:
    - 4桁数字パターンを検出し、既知銘柄セットでフィルタする `extract_stock_codes` を実装。
  - デフォルト RSS ソースとして Yahoo Finance ビジネスカテゴリの RSS を登録。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - DataSchema.md に基づくスキーマを実装（Raw / Processed / Feature / Execution の 3 層 + Execution）。
  - 多数のテーブル DDL を提供（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - インデックス定義（頻出クエリのためのインデックス）を用意。
  - `init_schema(db_path)` でディレクトリ作成含めてスキーマを初期化（冪等）。`:memory:` のサポートあり。
  - `get_connection(db_path)` で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の設計に沿ったモジュールを実装（差分取得、保存、品質チェックの導入ポイントを想定）。
  - ETL 実行結果を格納する `ETLResult` dataclass（品質問題のサマリ、エラーフラグ、to_dict 等）。
  - 差分取得補助: テーブル存在チェック、最大日付取得 `_get_max_date`、営業日調整 `_adjust_to_trading_day`。
  - raw_prices / raw_financials / market_calendar の最終取得日取得関数。
  - 個別ジョブ `run_prices_etl`（差分ロジック、backfill_days による後出し修正吸収のための再取得）を実装。（注: run_prices_etl の戻り値のタプル定義が途中で途切れている箇所あり）

### Security
- セキュリティ強化点（特記事項）
  - RSS パーサーは defusedxml を使用して悪意ある XML を防ぐ。
  - RSS フェッチ実装は SSRF 対策（ホストのプライベート判定、リダイレクトの検査）を含む。
  - .env の読み込みは OS 環境変数を保護する仕組み（protected keys）を用意。

### Internal / Tests
- テストしやすさのための設計上の配慮
  - `_urlopen` や id_token 注入により、外部 API やネットワークをモックしてユニットテストが可能。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` によりテスト環境での自動 .env 読み込みを無効化できる。

### Known issues / Notes
- run_prices_etl の末尾が途中で切れている（戻り値のタプルの2つ目が欠落）ため、そのままでは実行時に Syntax/Return の不整合が発生する可能性がある。実装の続き（戻り値の明確化と品質チェック処理の統合）が必要。
- strategy / execution / monitoring のパッケージ初期化ファイルは存在するが具体的実装は含まれていない（将来の拡張ポイント）。
- DuckDB の SQL を直接組み立てる箇所があり（プレースホルダ数が多いクエリ等）、非常に大きなチャンクでのパラメータ数上限に注意（既にチャンク分割で対策済み）。

### Breaking Changes
- 初回リリースのためなし。

### Removed
- なし

### Fixed
- なし

### Deprecated
- なし

---

貢献・バグ報告・改善提案は Issue / Pull Request にて受け付けてください。