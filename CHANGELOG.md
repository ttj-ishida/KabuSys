# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現状なし）

## [0.1.0] - 2026-03-17

初回公開リリース。以下の機能・設計方針を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - モジュールエクスポート: data, strategy, execution, monitoring。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を安全に読み込む自動ローダーを実装。
  - 自動ロードの優先順位: OS環境変数 > .env.local > .env。
  - テスト等で自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env パーサーは export 形式のサポート、クォート内のエスケープ、インラインコメント処理など細かな構文を扱う。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証、環境判定プロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用 API クライアントを追加。
  - レート制御: 固定間隔スロットリングに基づく RateLimiter（デフォルト 120 req/min）。
  - リトライロジック: 指数バックオフによる最大 3 回のリトライ（対象: 408/429/5xx、ネットワークエラー）。
  - 401 発生時はリフレッシュトークンで自動的にトークンを更新して 1 回再試行する仕組みを導入。
  - ページネーション対応（pagination_key の追跡・重複チェック）。
  - データ保存は DuckDB への冪等（ON CONFLICT DO UPDATE）で実装（raw_prices, raw_financials, market_calendar）。
  - 型変換ヘルパー（_to_float / _to_int）、フェッチ時刻の UTC 記録（fetched_at）により Look-ahead Bias のトレースが可能。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能を追加。
  - セキュリティ・堅牢性:
    - defusedxml を使った XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時のスキーム検査・プライベートアドレス検出、最終 URL の再検証、HTTP/HTTPS スキームのみ許可。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去）と記事 ID の SHA-256 によるハッシュ化（先頭32文字）で冪等性を確保。
  - 取得後の前処理: URL 除去、空白正規化（preprocess_text）。
  - DB 書き込みはチャンク化して一括 INSERT、トランザクションで処理。INSERT ... RETURNING を利用して実際に挿入されたレコードだけを返す。
  - 銘柄抽出: テキスト中の 4桁数字から known_codes に含まれる銘柄コードを抽出するユーティリティ。
  - run_news_collection により複数ソースを独立して収集、記事→news_symbols の紐付けを一括挿入。

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（+ Execution）に対応するテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions、processed（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）、features, ai_scores、signals, signal_queue, orders, trades, positions, portfolio_performance などを定義。
  - 適切な CHECK 制約、PRIMARY KEY、外部キー、インデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成、DDL を順序に従って冪等的に実行して初期化する機能を提供。get_connection() で既存 DB へ接続。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計に基づくユーティリティと差分更新ロジックを実装。
  - 最終取得日の取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダーを用いた非営業日調整機能（_adjust_to_trading_day）。
  - run_prices_etl 実装（差分取得、backfill デフォルト 3 日、取得→保存フロー）。差分更新の単位は営業日ベースで後出し修正に対応するため backfill を考慮。
  - ETLResult データクラスにより ETL 実行結果（取得件数、保存件数、品質問題、エラー要約）を集約。品質チェック（quality モジュール）との連携を想定。

- テスト容易性・拡張性
  - id_token の注入ポイントや _urlopen などモック差し替え可能な設計を採用。
  - ロギングを各処理に追加し監査・デバッグしやすくしている。

### Security
- RSS / XML の取り扱いで defusedxml を使用して潜在的な XML 攻撃を防止。
- ニュース収集での SSRF / 内部アドレスアクセス防止を包括的に実装（リダイレクト検査、IP 判定、DNS 解決時の保護）。
- .env 読み込みは OS 環境変数を protected として上書きを制御可能（override フラグと protected 引数）。

### Changed
- （該当なし — 初回リリース）

### Fixed
- （該当なし — 初回リリース）

### Removed
- （該当なし — 初回リリース）

---

注記：
- 当リリースはコードベースから推測して作成した CHANGELOG です。実際のリリースノート作成時は、実装・仕様変更点・既知の制限や互換性の注意事項を開発チームで確認のうえ反映してください。