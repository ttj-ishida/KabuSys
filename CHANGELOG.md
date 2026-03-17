# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従っています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初期公開リリース。

### 追加（Added）
- パッケージの基本構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
  - モジュール公開: data, strategy, execution, monitoring（strategy/execution/monitoring はプレースホルダ）
- 環境設定モジュール（kabusys.config）
  - .env ファイルおよび環境変数の読み込みを自動化（プロジェクトルートを .git または pyproject.toml から探索）
  - .env のパースは export KEY=val、クォート文字列、インラインコメント等に対応
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供し、以下の設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live、検証あり）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、検証あり）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース機能:
    - ID トークン取得（get_id_token）
    - 日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、市場カレンダー（fetch_market_calendar）の取得
  - 実装された設計/品質:
    - API レート制限遵守（120 req/min）: 固定間隔スロットリング _RateLimiter
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）
    - 401 発生時にリフレッシュトークンから自動で id_token を再取得して 1 回リトライ
    - ページネーション対応（pagination_key を使用）
    - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 防止）
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 型変換ユーティリティ (_to_float, _to_int)
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と raw_news への保存ワークフロー実装
  - 機能の概要:
    - RSS フィード取得（fetch_rss）、記事整形（preprocess_text）、ID 生成（正規化 URL → SHA-256 の先頭32文字）
    - defusedxml を用いた XML パース（XML Bomb などの対策）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないか検査（_is_private_host）
      - リダイレクト時にもスキームとホストを検証する _SSRFBlockRedirectHandler
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍時のサイズチェック（Gzip bomb 対策）
    - トラッキングパラメータ除去（utm_* / fbclid / gclid 等）とクエリのソートによる URL 正規化
    - DuckDB への冪等保存:
      - save_raw_news: チャンク分割、トランザクション、INSERT ... RETURNING により新規挿入のみを返す
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存、ON CONFLICT DO NOTHING、挿入件数を正確に返す
    - 銘柄抽出: テキストから 4 桁の銘柄コード候補を抽出し、与えられた known_codes セットでフィルタ（extract_stock_codes）
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを含む
  - モジュールはテスト支援のため _urlopen を差し替え可能に実装
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーのテーブル定義を実装
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリポイント用）
  - テーブル作成順を考慮した DDL 列挙
  - init_schema(db_path) によりディレクトリ自動作成 → テーブル/インデックス作成 → DuckDB 接続を返す
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・保存・品質チェックを想定した ETLResult データクラスを実装
  - 差分更新ヘルパー:
    - raw_prices/raw_financials/market_calendar の最終取得日取得関数
  - 市場カレンダー補正: 非営業日の場合に直近営業日に調整する _adjust_to_trading_day
  - run_prices_etl の骨子（差分算出、バックフィル日数設定、J-Quants からの取得と保存）を実装
  - 設定値:
    - 最古データ日: 2017-01-01
    - 市場カレンダー先読み: 90 日
    - デフォルト backfill_days: 3
  - 品質チェックモジュール（quality）との連携を想定（QualityIssue を参照）

### セキュリティ（Security）
- news_collector:
  - defusedxml による XML パースで XML 攻撃を軽減
  - SSRF 対策: URL スキーム検証、プライベートアドレス判定、リダイレクト時の検査
  - レスポンスサイズ・gzip 解凍後サイズ上限を設けることでメモリ DoS を軽減
- jquants_client:
  - タイムアウト設定（urllib でのタイムアウト）および堅牢なエラーハンドリングとリトライ

### 既知の制限 / 注意点（Known issues）
- strategy、execution、monitoring パッケージは __init__ が存在するのみで実装は未着手（プレースホルダ）。
- run_prices_etl の戻り値処理に不完全な箇所がある（現状のコード断片では fetched/saved の組み合わせの戻り値が途中で切れているように見える）。ETL の詳細なエラーハンドリングや品質チェックの統合は今後整備予定。
- save_raw_news / save_news_symbols は DuckDB の SQL を直接構築して実行しているため、将来的に SQL インジェクションのリスクや SQL 長の問題に注意（現状では内部データソースを想定しているため問題は限定的）。
- news_collector の DNS 解決失敗時は安全側（非プライベート）と判断し通過させる実装になっている。運用上のポリシーに応じた挙動変更が必要な場合がある。

### ドキュメント / 運用メモ（Notes）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行う。CI / テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- デフォルトの DuckDB 保存先は data/kabusys.duckdb。init_schema() を使って初回作成すること。
- J-Quants API のレート制限（120 req/min）を厳守する実装が組み込まれているが、極端に並列化された利用や長時間の連続実行では運用上の監視が必要。

### 互換性に関する注記（Breaking Changes）
- 初期リリースのため破壊的変更はありません。

---

今後の予定（短期）
- ETL の完全実装（保存時の品質チェック統合とエラーハンドリングの強化）
- strategy / execution / monitoring モジュールの実装
- 単体テスト・統合テストの整備、CI パイプライン構築
- ドキュメント（DataPlatform.md, API 使用例、運用手順）の追加

（以上）