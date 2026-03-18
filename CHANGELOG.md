# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

全てのリリースは SemVer に従います。

## [Unreleased]

（現在の開発ブランチに対する未リリースの変更をここに記載します）

---

## [0.1.0] - 2026-03-18

初回公開リリース。以下の主要機能とモジュールを追加しました。

### Added
- パッケージ初期化
  - pakage: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定/環境管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理をサポート）。
  - settings オブジェクトを提供し、J-Quants・kabuステーション・Slack・DBパス・システム設定（KABUSYS_ENV/LOG_LEVEL）などのプロパティを透過的に取得。
  - 環境値のバリデーション（有効な環境値・ログレベルのチェック）と必須変数取得時のエラーメッセージを実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装（ページネーション対応）。
  - レート制限（120 req/min）を満たす固定間隔スロットリング RateLimiter を導入。
  - 再試行（指数バックオフ、最大3回）を実装。対象ステータス 408/429/5xx を再試行対象とする。
  - 401 Unauthorized 受信時に自動でリフレッシュトークンから id_token を取得して 1 回だけリトライするロジックを実装（無限再帰防止のため allow_refresh 制御あり）。
  - JSON デコード失敗時の明瞭なエラーメッセージ、タイムアウトやネットワークエラー時のログと再試行。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアス対策を考慮。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を担保し、PK 欠損行はスキップして警告ログ出力。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する処理を実装（デフォルトに Yahoo Finance のビジネスカテゴリを含む）。
  - defusedxml を用いた XML パースで XML Bomb 等への対策を実施。
  - SSL/HTTP リダイレクト時の事前検証ハンドラ（SSRFBlockRedirectHandler）を実装し、リダイレクト先のスキームやプライベートアドレスへの到達を防止。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid など）、SHA-256（先頭32文字）から生成する記事ID による冪等性確保。
  - レスポンスサイズ上限（10 MB）および gzip 解凍後のサイズチェックを導入し、DoS 対策を実施。
  - 記事本文の前処理（URL除去、空白正規化）と pubDate の robust なパース（RFC2822→UTC）を実装。
  - DuckDB への保存はチャンク単位で INSERT ... RETURNING を使用し、新規挿入IDのリストを返す。トランザクションにより挿入失敗時はロールバック。
  - 記事と銘柄コードの紐付け（news_symbols）を一括挿入するユーティリティを実装。既存ペアは ON CONFLICT でスキップし、正確な挿入数を返す。
  - テキスト中から4桁銘柄コードを抽出する関数（known_codes に基づくフィルタリングと重複除去）を提供。
  - run_news_collection により複数 RSS ソースを安全に収集し、各ソースは独立してエラー処理（1ソース失敗でも他は継続）する。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform.md に基づき、Raw / Processed / Feature / Execution 層を含むスキーマ定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution 層。
  - 各種制約（PRIMARY KEY、CHECK）、外部キー、頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) で親ディレクトリ自動作成、全テーブル/インデックス作成を行い、冪等な初期化を提供。get_connection() による既存 DB への接続も提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック実装（DB の最終取得日を元に date_from を自動算出、backfill_days による後出し修正吸収）。
  - run_prices_etl 等の個別 ETL ジョブを実装（取得→保存→品質チェックの流れ、id_token を引数注入可能）。
  - ETLResult データクラスを追加し、取得/保存数、品質問題、エラー一覧などを集約。品質問題は severity による判定（エラー重大度を検出可能）。
  - 市場カレンダーを参照して非営業日の調整を行うヘルパー（_adjust_to_trading_day）を実装。
  - テーブル存在チェック、最大日付取得ユーティリティを提供。

### Security
- RSS/HTTP 周りの SS F R 対策を強化
  - リダイレクト前後でスキームとホストを検証し、http/https 以外やプライベートアドレスへのアクセスを拒否。
  - defusedxml を用いて XML 関連攻撃（XML External Entity / XML Bomb 等）を防止。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズチェックによりメモリ DoS を軽減。
  - URL スキーム検証で file:, javascript:, mailto: などを排除。
- .env 読み込みでは OS 環境変数を保護する protected 機構を実装（.env.local は override 可だが既存の OS 環境変数は保持）。

### Notes / Design Decisions
- J-Quants API クライアントはページネーション、取得時刻の記録、冪等な DB 書き込み（ON CONFLICT）を重視して設計。
- ニュース記事の ID を URL 正規化＋ハッシュで生成することで、トラッキングパラメータの違いによる重複挿入を防止。
- ETL は Fail-Fast とせず、品質チェックで問題があっても処理を継続し呼び出し元に問題を報告する方針。
- DuckDB スキーマは外部キーやCHECK制約を用いてデータ整合性を担保しつつ、検索性能のためにインデックスを追加。

### Known limitations / TODO
- strategy / execution / monitoring パッケージの実装詳細は本リリースでは最小限（__init__.py の公開のみ）。今後のリリースでアルゴリズムや発注連携を追加予定。
- pipeline.run_prices_etl の一部実装（戻り値周りや・追加のETLジョブ統合）は今後継続して整備予定。
- 単体テスト・統合テスト、外部 API を模したモック/フェイクの充実化は今後の課題。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートはプロジェクトのコミット履歴やリリース管理情報に基づき更新してください。）