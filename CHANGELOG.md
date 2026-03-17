# Changelog

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に従っています。
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システムの基盤機能を実装しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"、__all__ の定義）。
- 環境設定/ローディング (kabusys.config)
  - .env ファイルまたは環境変数から設定をロードする Settings クラスを実装。
  - 自動 .env 読み込み機能を提供（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env の柔軟なパース実装（コメント、export プレフィックス、クォート、インラインコメント処理を考慮）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 環境値の検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）と必須値取得時の明示的エラー（_require）。
  - DBパス設定（duckdb, sqlite）や API/Slack 関連の必須キーを Settings 経由で取得可能に。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回のリトライ（408, 429, 5xx 対応）。
  - 401 Unauthorized を検知した場合の ID トークン自動リフレッシュ（最大 1 回リトライ）とモジュールレベルのトークンキャッシュ（ページネーション間で共有）。
  - 取得時刻（fetched_at）を UTC で付与して Look-ahead バイアス対策。
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes: raw_prices へ保存
    - save_financial_statements: raw_financials へ保存
    - save_market_calendar: market_calendar へ保存
  - 値変換ユーティリティ（_to_float, _to_int）を実装し、型変換の頑健性を向上。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news テーブルへ保存する機能を実装。
  - デフォルト RSS ソースに Yahoo Finance (日本経済カテゴリ) を追加。
  - セキュリティ・堅牢性:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - SSRF 対策: 非 http/https スキーム拒否、プライベート/ループバックアドレス拒否、リダイレクト時の検証用ハンドラ実装。
    - レスポンスサイズ上限（10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - fetch_rss: RSS 取得→パース→記事整形（URL除去、空白正規化）を実装。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を使って実際に挿入された記事IDリストを返す（チャンク挿入、トランザクション管理）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（チャンク化 & RETURNING、トランザクション）。
  - extract_stock_codes: テキストから 4 桁銘柄コードを抽出するユーティリティ（重複除去、known_codes フィルタ）。
  - run_news_collection: 全ソースを巡回して記事取得→保存→（オプションで）銘柄紐付けを行う統合ジョブ。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md 準拠の DuckDB スキーマを実装（Raw / Processed / Feature / Execution の各レイヤ）。
  - 各種テーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主要クエリ向けのインデックスを作成（code/date や status 用など）。
  - init_schema(db_path) により親ディレクトリ自動作成およびテーブル/インデックス作成（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を導入し、ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
  - 差分更新ヘルパー: テーブルの最終取得日を取得する関数を提供（get_last_price_date 等）。
  - 市場カレンダー補正: 非営業日の場合に直近の過去営業日に調整する _adjust_to_trading_day を実装。
  - run_prices_etl: 株価差分 ETL 実装（差分開始日の自動算出、バックフィル日数サポート、jquants_client の fetch/save 呼び出し）。
  - ETL の設計方針: 差分更新、backfill（デフォルト3日）、品質チェックは fail-fast しない設計（quality モジュールと連携想定）。

### 変更 (Changed)
- （初版のため履歴上の「変更」はありません）

### 修正 (Fixed)
- （初版のため履歴上の「修正」はありません）

### セキュリティ (Security)
- RSS パーサに defusedxml を使用し XML に起因する攻撃を軽減。
- RSS/HTTP クライアントに対して SSRF 対策を多数実装（スキーム検証、プライベートアドレス判定、リダイレクト時検査）。
- ネットワーク/HTTP レスポンスに対するサイズ上限を設け、メモリ DoS / Gzip Bomb に対処。

### 既知の注意点 (Notes)
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布パッケージや別作業ディレクトリで動作させる際は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定するか、明示的に環境変数を設定してください。
- ETL と品質チェックの連携（quality モジュール）の実装は本バージョンでは参照を含むが、品質チェックの具体的な実装状況により挙動が異なります（quality.QualityIssue 型が使用されています）。
- run_prices_etl は本コード断片の末尾で途中（戻り値のタプル整形が切れているように見える）となっている可能性があります。実装の完全性を確認してください（本 CHANGELOG はコードの現状から推測して作成しています）。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

----

今後のリリースでは、監視・実行モジュール（execution）、戦略モジュール（strategy）、品質検査の詳細実装、テスト補強、CI/CD・デプロイ手順などを追加予定です。