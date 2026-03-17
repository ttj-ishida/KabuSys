# Changelog

すべての変更は Keep a Changelog 規約に従い、重要な変更はセマンティックバージョニングを使用しています。
リリース日付は本リリース作成日です。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-17
初回公開リリース。日本株自動売買システムのコア基盤を実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。バージョンを 0.1.0 に設定。
  - public API として data, strategy, execution, monitoring を公開。

- 環境設定管理
  - `kabusys.config.Settings` を実装し、環境変数から各種設定を取得する API を提供（J-Quants, kabuステーション, Slack, DB パスなど）。
  - .env 自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env のパース機能を強化（export プレフィックス対応、クォート内エスケープ、コメント処理）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
  - settings インスタンスを提供。

- J-Quants データクライアント
  - `kabusys.data.jquants_client` を追加。
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch 関数を実装（ページネーション対応）。
  - API レート制御（固定間隔スロットリング）により 120 req/min を遵守。
  - 再試行（指数バックオフ、最大 3 回）および 401 受信時の自動トークンリフレッシュを実装。
  - レスポンス JSON のデコードエラーやネットワークエラーに対する扱いを明確化。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等保存を行う。
  - 値変換ユーティリティ（_to_float, _to_int）を実装して不正データ耐性を向上。

- ニュース収集 (RSS)
  - `kabusys.data.news_collector` を追加。
  - RSS フィードから記事を取得して raw_news に保存する一連の処理（fetch_rss, save_raw_news, save_news_symbols, _save_news_symbols_bulk, run_news_collection）を実装。
  - 記事IDを正規化 URL の SHA-256（先頭32文字）で生成し、重複挿入を防止する設計。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）を実装。
  - XML パースに defusedxml を使用して XML Bomb 等の脆弱性に対処。
  - SSRF 対策
    - http/https のみ許可するスキーム検証。
    - リダイレクト先のスキーム・ホスト検証（プライベート/ループバック/リンクローカル/マルチキャストの拒否）。
    - レスポンスサイズ上限（10 MB）を設け、gzip 解凍後のサイズ検査を実施。
  - テキスト前処理（URL 除去、空白正規化）。
  - 記事保存はチャンク化してトランザクションでまとめ、INSERT ... RETURNING を利用して実際に挿入された件数を正確に取得。
  - 記事中からの銘柄コード抽出（4桁）と既知銘柄セットによるフィルタリング機能を提供。

- DuckDB スキーマ定義
  - `kabusys.data.schema` を追加。Raw / Processed / Feature / Execution 層に対応するテーブル定義（DDL）を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
  - features, ai_scores の Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - 頻出クエリ向けのインデックス定義を提供。
  - `init_schema(db_path)` により DB ファイルの親ディレクトリ作成と DDL 実行を行い、冪等に初期化可能。
  - `get_connection(db_path)` で既存 DB へ接続するユーティリティを提供。

- ETL パイプライン
  - `kabusys.data.pipeline` を追加。
  - 差分更新（最終取得日に基づく再取得・バックフィル）と J-Quants client 連携を行う ETL ジョブの骨組みを実装。
  - データ品質チェックのフック（quality モジュール想定）に対応する ETLResult を定義（品質問題とエラーの集約、シリアライズ用 to_dict）。
  - 市場カレンダーを考慮した営業日調整、各リソースの最終取得日取得ユーティリティを実装。
  - run_prices_etl などの個別 ETL ジョブの開始実装（差分計算、fetch → save の処理フロー、バックフィル設定）。

### 変更 (Changed)
- —（初回リリースのため既存変更はなし）

### 修正 (Fixed)
- —（初回リリースのため修正はなし）

### セキュリティ (Security)
- RSS パーサに defusedxml を使用して XML 脆弱性を緩和。
- RSS フェッチ時に SSRF 対策を実装（スキームチェック、プライベート IP チェック、リダイレクト検査）。
- ネットワークから読み込むデータのサイズ制限（MAX_RESPONSE_BYTES = 10 MB）を導入。

### 既知の制限・注意点 (Notes)
- quality モジュールは外部に依存する想定でパイプラインから参照しており、別途実装が必要。
- strategy/execution/monitoring パッケージは初期化ファイルのみで、実装はこれから追加予定。
- DuckDB 用のスキーマは初期化時に作成されるが、既存データとの互換性確認は必須。
- J-Quants のレート制約や API 仕様は変わる可能性があり、運用時に監視が必要。

---
記載内容はコードベースから推測して作成しています。実装方針や詳細が設計書と異なる場合は、差分を反映して更新してください。