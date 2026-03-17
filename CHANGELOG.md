# Changelog

すべての公開変更点は Keep a Changelog の形式に従って記述します。  
このプロジェクトはセマンティックバージョニングを使用します。

現在のバージョン: 0.1.0 — 初期リリース

## [Unreleased]
- （今後の変更を記載）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」の基本的なデータ収集・保存・ETL基盤を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）とバージョン識別子を追加（0.1.0）。
  - モジュールの公開 API 指定（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env の行パーサ（export 形式、クォート処理、インラインコメント対応）。
  - 上書き制御（override）、保護キー（protected）により OS 環境変数を保護。
  - Settings クラスによる型付きアクセス:
    - J-Quants / kabu API / Slack / DB パス等の必須/省略時デフォルト設定。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/...）。
    - is_live/is_paper/is_dev ヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース機能:
    - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
  - レート制御:
    - 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行ロジック:
    - 指数バックオフ、最大 3 回のリトライ。対象ステータス: 408, 429, 5xx。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証/トークン管理:
    - リフレッシュトークン→IDトークン取得（get_id_token）。
    - モジュールレベルの ID トークンキャッシュ（ページネーション間共有）。
    - 401 受信時は自動でトークンをリフレッシュして 1 回リトライ。
  - DuckDB 保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar で冪等的保存（ON CONFLICT DO UPDATE）。
    - fetched_at を UTC で付与して「いつ知り得たか」をトレース可能に。
  - ユーティリティ:
    - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値は None）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS 取得と記事整備機能:
    - RSS フィード取得 (fetch_rss)、前処理（URL除去、空白正規化）、pubDate パース。
    - defusedxml を使用した安全な XML パース（XML bomb 対策）。
    - gzip 圧縮対応と受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）。
    - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。
    - トラッキングパラメータ（utm_* 等）の除去、クエリソート、フラグメント除去による URL 正規化。
    - RSS に不正なスキームやプライベートホストが含まれる場合は取得をスキップ。
  - SSRF 対策:
    - リダイレクト時の検査を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカルでないことを検査（DNS 解決も実施）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING を用いて新規挿入 ID を正確に取得。チャンク単位で一括挿入し 1 トランザクションでコミット。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク挿入で実装（重複除去、TRANSACTION）。
  - 銘柄コード抽出:
    - 正規表現で 4 桁数字を検出し、known_codes に基づいてフィルタリング（重複排除）。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用 DDL を整備（Raw / Processed / Feature / Execution 層）。
  - 各種テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各カラムに適切な型・チェック制約・PRIMARY KEY / FOREIGN KEY を設定。
  - 頻出クエリ向けインデックスを作成。
  - init_schema(db_path) によりディレクトリ自動作成 → 全テーブル・インデックスの作成を行い、DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計と基本実装:
    - 差分更新（DB の最終取得日を参照し未取得分のみ取得）。
    - backfill_days により後出し修正を吸収（デフォルト 3 日）。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）。
  - 結果表現:
    - ETLResult dataclass を追加（取得件数・保存件数・品質問題・エラー一覧などを保持）。
    - 品質チェックモジュール（quality）との連携を想定した構造（品質問題の severity を扱う）。
  - 個別 ETL ジョブ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - run_prices_etl: 差分取得のロジックと jquants_client を使った取得・保存の流れを実装（取得範囲の自動算出、ログ出力）。

### 変更 (Changed)
- 初期リリースのため特記事項なし。

### 修正 (Fixed)
- 初期リリースのため特記事項なし。

### セキュリティ (Security)
- RSS パースに defusedxml を採用（XML エンティティ攻撃対策）。
- RSS フェッチ時の SSRF 対策を実装（プライベートアドレスの拒否、リダイレクト検査、スキーム検証）。
- ネットワーク入力に対するサイズ制限（10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
- .env 読み込みで OS 環境変数の上書きを保護する機能を実装。

### パフォーマンス (Performance)
- API レート制御と指数バックオフによりリクエストの安定性を確保。
- DuckDB への挿入はチャンク分割とトランザクションで行い、オーバーヘッドを削減。
- INSERT ... RETURNING を用いて実際に挿入されたレコード数を正確に把握。

### 既知の制限 / 注意事項 (Known issues / Notes)
- pipeline.run_prices_etl のソースは ETL フロー実装済みだが、呼び出し側での統合や品質チェックの適用は今後の実装/検証が必要。
- 現在の .env パーサは一般的な形式に対応するが、極端に複雑なシェル式評価等はサポートしない。
- DuckDB をストレージとして利用しているため、運用環境ではバックアップ・ファイル運用の方針を検討してください。

---

（この CHANGELOG はソースコードから設計方針・実装内容を推測して作成しています。実際のリリースノートとして使用する際は、変更差分・コミット履歴に基づいて適宜補正してください。）