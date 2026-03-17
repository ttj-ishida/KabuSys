# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティック バージョニングを採用しています。

次の変更履歴は、提供されたコードベースの内容から推測して作成した初期リリース記録です。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システムの基盤機能を導入。

### Added
- パッケージ基盤
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"`、公開モジュール一覧 (`data`, `strategy`, `execution`, `monitoring`) を定義。
- 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート判定は `.git` または `pyproject.toml` による探索を採用（__file__ を起点に探索）。
  - .env のパース実装：コメント、`export KEY=val` 形式、シングル/ダブルクォートやバックスラッシュエスケープ対応、インラインコメント処理を考慮。
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。読み込み順は OS 環境 > .env.local > .env。
  - 必須値取得用 `_require`、環境名・ログレベルのバリデーション、データベースパス（DuckDB/SQLite）や Slack / kabuAPI / J-Quants トークン等のプロパティを提供。
- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本機能: ID トークン取得、株価日足（OHLCV）・財務データ（四半期 BS/PL）・市場カレンダー取得関数を提供。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する `_RateLimiter` を実装。
  - 再試行戦略: 指数バックオフ、最大 3 回リトライ、408/429/5xx を対象、429 の場合は `Retry-After` ヘッダを優先。
  - 401 ハンドリング: 受信時にトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - ページネーション対応（`pagination_key` に基づく連続取得）。
  - DuckDB への冪等保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を実装。`ON CONFLICT DO UPDATE` による上書きで重複を排除し、fetched_at を UTC で記録して Look-ahead Bias を抑制。
  - データ変換ユーティリティ `_to_float`, `_to_int` を実装（型安全性・不正値処理を考慮）。
- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集するフローを実装（フェッチ → 前処理 → DB 保存 → 銘柄紐付け）。
  - セキュリティ: defusedxml による XML パース、SSRF 対策（スキーム検証、プライベートIP/ホストの検出、リダイレクト時の検査）、Content-Length/受信バイト上限（10MB）や gzip 解凍後のサイズ検査（Gzip bomb 対策）を実装。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 先頭32文字）で冪等性を担保。
  - テキスト前処理（URL除去・空白正規化）と RSS pubDate の堅牢なパース（UTC への変換、失敗時は現在時刻で代替）。
  - DB 保存: `save_raw_news`（チャンク挿入、トランザクション、`INSERT ... RETURNING id` による新規件数取得）および `save_news_symbols` / `_save_news_symbols_bulk`（銘柄紐付け）を実装。
  - 銘柄抽出: 正規表現による 4 桁数字抽出と known_codes によるフィルタリング（重複排除）を実装。
  - デフォルト RSS ソース（例: Yahoo Finance ビジネスカテゴリ）を定義。
- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution の 3 層（+実行層）に基づくテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに制約（PRIMARY KEY, CHECK 等）を付与してデータ整合性を担保。
  - 頻出クエリ向けにインデックスを定義（コード×日付検索、ステータス検索等）。
  - `init_schema(db_path)` によりディレクトリ自動作成とテーブル/インデックスの冪等作成、`get_connection` を提供。
- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新とバックフィル（既存最終取得日から指定日数前を再取得して API 後出し修正を吸収）を行う ETL ロジックを実装（設計文書に基づく）。
  - 市場カレンダーの先読み、最小データ開始日設定。
  - ETL 実行結果を表す `ETLResult` dataclass を導入（取得件数・保存件数・品質問題・エラーなどを保持、辞書化メソッドを提供）。
  - DB 存在チェックや最大日付取得のユーティリティ、営業日への調整ロジックを実装。
  - 個別 ETL ジョブ（例: `run_prices_etl`）の基礎を実装（差分計算、fetch→save の呼び出し）。※ファイル末尾で run_prices_etl が途中まで記載（推測部分あり）。
- 依存関係（コード内で参照）
  - duckdb, defusedxml を使用する旨の実装。

### Changed
- 該当なし（初回リリース）。

### Fixed
- 該当なし（初回リリース）。

### Security
- RSS/XML 処理における XML Entity 攻撃対策として defusedxml を使用。
- RSS フェッチ時に SSRF を抑止するためのスキーム・プライベートホスト検査、リダイレクト時の検査を導入。
- ネットワーク読み込みに対して最大受信バイト数を設定し、Gzip 解凍後のサイズ検査を行うことでメモリ DoS / Gzip bomb に対処。

### Notes / Important configuration
- 必須の環境変数（例）:
  - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知用）
- 自動 .env ロードはデフォルトで有効。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB スキーマ初期化は `init_schema()` を使用してください。`get_connection()` は既存 DB への接続のみ（初期化は行わない）。

### Known limitations / TODO
- ETL パイプラインの一部（例: run_prices_etl の戻り値表現や他ジョブ）はコード内で途中まで実装されており、完全なジョブ連携・品質チェック（quality モジュールの連携）やエラーハンドリングポリシーの最終確定が必要。
- strategy / execution / monitoring パッケージはパッケージ構造として存在するが、具体的な実装は未提供（今後追加予定）。
- 単体テスト、統合テスト、API のモックを用いたテストカバレッジの整備が推奨される。

---

（注）上記は提供されたソースコードの内容とコメントから推測して作成した CHANGELOG です。実際のリリース手順や公開日、変更点の詳細はプロジェクトのリリース運用に合わせて調整してください。必要であれば、各機能ごとにより詳細なリリースノート（例: API の使用例、戻り値仕様、例外一覧）も作成します。