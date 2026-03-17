# CHANGELOG

すべての注目すべき変更はここに記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  
以下のリリースノートは提示されたコードベースの実装内容から推測して作成しています。

## [0.1.0] - 2026-03-17
初回リリース（ベース実装）。以下の主要機能・設計方針を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを定義（kabusys.__version__ = 0.1.0、__all__ に data/strategy/execution/monitoring を公開）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を探索してルートを特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効に可能。
  - .env の行パーサを実装（export プレフィックス、クォート、コメント、エスケープ対応）。
  - 環境変数の必須チェック (_require) と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境判定等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。
- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライ戦略（最大3回、指数バックオフ、408/429/5xx 対象）。
    - 401 発生時はリフレッシュトークンから id_token を自動更新して1回リトライ。
    - ページネーション対応（pagination_key の扱い）。
    - 取得日時（fetched_at）を UTC で記録し Look-ahead Bias を抑制。
    - データ保存は冪等化（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
  - fetch/save 関数を実装:
    - fetch_daily_quotes / save_daily_quotes（raw_prices テーブル向け）
    - fetch_financial_statements / save_financial_statements（raw_financials）
    - fetch_market_calendar / save_market_calendar（market_calendar）
  - 型変換ユーティリティ (_to_float / _to_int) を実装（安全な変換と不正値処理）。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集する機能を実装。
    - デフォルトソースに Yahoo Finance のカテゴリ RSS を定義。
    - 記事IDは正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_ 等）、フラグメント除去、クエリソート。
    - テキスト前処理（URL 除去、空白正規化）。
    - SSRF 対策:
      - リダイレクト時にスキームとホストが http/https かつパブリックであることを検証するカスタムリダイレクトハンドラを実装。
      - fetch 前にホストがプライベートかを検査。
    - XML 攻撃対策: defusedxml を利用して XML をパース（XML Bomb 等への配慮）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - DB への保存はトランザクションにまとめ、チャンク単位で INSERT ... RETURNING を利用して実際に挿入された ID/件数を返す（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。
    - 銘柄コード抽出機能を提供（4桁数字、既知コードフィルタリング）。
    - テスト容易性のため _urlopen の差し替え（モック）を想定。
- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用の包括的スキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
    - 生データ: raw_prices, raw_financials, raw_news, raw_executions
    - 加工済み: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - 特徴量層: features, ai_scores
    - 実行層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）と索引（頻出クエリ向けインデックス）を設定。
  - init_schema(db_path) でディレクトリ作成 → スキーマ作成 → DuckDB 接続を返すユーティリティを提供。get_connection も提供。
- ETL パイプライン基盤 (kabusys.data.pipeline)
  - 差分更新を中心とした ETL ロジックの基礎を実装。
    - 最終取得日の照会ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 非営業日調整ヘルパー（_adjust_to_trading_day）。
    - run_prices_etl（差分取得・バックフィルロジック）および ETLResult dataclass により ETL 実行結果を表現。
    - backfill_days による後出し修正吸収（デフォルト 3 日）。
    - 市場カレンダーの先読み（設計値を定数で定義）。
  - 品質チェック（quality モジュール）と連携する設計（重大度判定などを想定）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML 関連攻撃を軽減。
- RSS フェッチ時に SSRF リスクを低減する複数のチェックを導入（スキーム検証、プライベート IP チェック、リダイレクト検査）。
- レスポンスサイズ制限と gzip 解凍後の再チェックによりメモリ DoS / Gzip bomb を防止。

### 内部 (Internal)
- モジュール単位でテストを容易にする設計:
  - jquants_client: id_token を注入可能（テスト用にキャッシュ／強制リフレッシュの制御）。
  - news_collector: _urlopen をモック差し替え可能。
- ロギングを各モジュールで利用して処理状況・警告を出力（fetch/save 関数で取得件数/保存件数等をログ出力）。

---

注記:
- 本 CHANGELOG は提示されたコードの内容から推測して作成しています。実際のリリースノートに含める場合は、リリース日・著者・関連 Issue/PR 等を適宜付与してください。