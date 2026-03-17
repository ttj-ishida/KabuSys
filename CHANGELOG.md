# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" のガイドラインに準拠しています。
リリース日はコミット時点の推定日（本ファイル作成日: 2026-03-17）です。

なお、本CHANGELOGは提示されたソースコードから機能追加・仕様を推測して作成しています。

## [Unreleased]

### Known issues / 注意点
- run_prices_etl の戻り値処理に未完（ソース上で `return len(records),` のように2要素目が欠けている箇所が見受けられます）。ETL呼び出し側で期待するタプル (fetched, saved) を返すよう修正が必要です。
- 単体テスト用のモックポイント（例: news_collector._urlopen や config の自動環境変数ロードの無効化）が用意されていますが、テストケースは別途整備が必要です。

---

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ:
    - __version__ = "0.1.0"
    - 公開サブモジュール: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env および .env.local ファイルの自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して検出）
  - 読み込み優先度: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env の各行パーサ実装（export 形式、クォート内エスケープ、インラインコメント取り扱い、無効行スキップ）
  - 設定取得用 Settings クラスを実装（J-Quantsトークン、kabu API、Slack、DB パス、環境種別、ログレベルなど）
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
  - 必須環境変数未設定時に ValueError を送出する _require ユーティリティ

- データ収集クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアント実装
  - 機能:
    - ID トークン取得 (get_id_token)
    - 株価日足取得 (fetch_daily_quotes) — ページネーション対応
    - 財務データ取得 (fetch_financial_statements) — ページネーション対応
    - 市場カレンダー取得 (fetch_market_calendar)
  - 設計上の重要点:
    - レートリミッタ実装（固定間隔スロットリング、120 req/min に合わせた最小間隔）
    - リトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx をリトライ対象）
    - 401 受信時の自動トークンリフレッシュ（1回まで）と再試行
    - JSON デコード失敗時の明示的なエラー
    - 取得時刻 (fetched_at) を UTC ISO 形式で記録する方針（Look-ahead bias 対策の注釈）
  - DuckDB 保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装
    - ON CONFLICT DO UPDATE による冪等保存（重複更新対応）
    - 主キー欠損行のスキップとログ出力

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集および DuckDB への保存処理を実装
  - 機能:
    - fetch_rss: RSS 取得とパース（defusedxml を利用）、gzip 解凍、サイズ上限チェック（MAX_RESPONSE_BYTES=10MB）
    - preprocess_text: URL 除去・空白正規化
    - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES）
    - 記事ID の生成は正規化 URL の SHA-256 ハッシュ先頭32文字（_make_article_id）で冪等性を担保
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/IP リンクローカルかをチェックする _is_private_host
      - リダイレクト時にもスキーム・プライベートアドレスを検査するカスタム RedirectHandler
    - save_raw_news: INSERT ... RETURNING id を用いたチャンク一括挿入、トランザクションでの安全な保存
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複スキップ、挿入数を正確に返す）
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出し known_codes に基づいてフィルタ
    - run_news_collection: 複数ソースの統合収集ジョブ（各ソースは独立処理、1ソース失敗でも他は継続）

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 向けのスキーマ定義と初期化ロジックを実装
  - Raw / Processed / Feature / Execution の各レイヤーをカバーするテーブル群を定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（NOT NULL、PRIMARY KEY、CHECK）を多用してデータ整合性を担保
  - インデックス定義（典型的なクエリパターン向け）
  - init_schema(db_path) でディレクトリ作成 → 接続 → DDL 実行（冪等）
  - get_connection(db_path) で既存 DB への接続を提供（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL モジュール骨格を実装
  - 機能:
    - ETLResult データクラスによる実行結果集計（品質問題やエラー情報を含む）
    - DB 内の最終日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）
    - trading day 調整ヘルパー（_adjust_to_trading_day）
    - run_prices_etl: 差分取得ロジック（最終取得日から backfill_days 分を巻き戻し再取得）と jquants_client を使った取得→保存手順の開始
  - 設計方針:
    - 差分更新（最小単位は営業日1日分）
    - backfill_days による後出し修正吸収
    - 品質チェックは別モジュール (kabusys.data.quality) と連携する想定（errors を収集して ETL 継続）

### Security
- RSS XML パーサに defusedxml を使用し XML Bomb 等の脆弱性を緩和
- ニュース取得で SSRF 対策を実装（スキームホワイトリスト、プライベートIP検査、リダイレクト検査）
- .env 読み込み時に OS 環境変数を保護する protected セットを導入（既存環境変数が上書きされない仕様）

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし。ただし上記 Known issues を参照）

---

参考: 今後の推奨改善点（実装推奨）
- run_prices_etl の戻り値修正（fetched, saved を確実に返す）
- ユニットテスト・CI の整備（network dependent 部分はモック化）
- jquants_client のログ／メトリクス強化（レート制限・リトライ統計）
- news_collector のソース毎の並列実行サポート（ただし SSRF チェックとリソース制限に注意）
- データ品質チェックモジュールの実装および ETLResult との統合

--- 

[0.1.0]: 0.1.0 - 2026-03-17