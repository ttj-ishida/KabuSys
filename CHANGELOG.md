# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリースはセマンティックバージョニングに従います（例: MAJOR.MINOR.PATCH）。
- 日付はコードベースから推測した初回公開日を使用しています。

## [Unreleased]

（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-17 (推定)

初期公開リリース。日本株自動売買プラットフォームの骨組みを実装しました。主な追加点は以下の通りです。

### 追加 (Added)

- パッケージ基盤
  - パッケージ名: kabusys、バージョン文字列: 0.1.0
  - パッケージ公開用 __all__ を定義（data, strategy, execution, monitoring）

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルや環境変数から設定を読み込む自動ローダを実装
    - 読み込み順序: OS 環境 > .env.local > .env
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
  - .env パーサ実装（export 形式、クォート・エスケープ、インラインコメント等を考慮）
  - 必須環境変数取得ヘルパー _require を提供（未設定時に ValueError を送出）
  - Settings クラスを提供（プロパティ経由で J‑Quants / kabu API / Slack / DB パス / 環境モード等を取得）
    - 環境値検証: KABUSYS_ENV (development|paper_trading|live)、LOG_LEVEL（DEBUG..CRITICAL）

- データ取得クライアント (kabusys.data.jquants_client)
  - J‑Quants API クライアントを実装
    - ベース URL、ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供
    - API レート制限遵守（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
    - JSON デコードエラーやネットワーク例外への詳しいエラーメッセージ
  - DuckDB 保存ユーティリティ
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複・更新を処理
    - fetched_at を UTC ISO 形式で保存し、データ取得時点をトレース可能に

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集・正規化して DuckDB に保存する機能を実装
    - デフォルト RSS ソース: Yahoo Finance（news.yahoo.co.jp のビジネスカテゴリ）
    - XML パースは defusedxml を使用し XML Bomb 等の攻撃を軽減
    - レスポンス受信バイト数上限（MAX_RESPONSE_BYTES = 10 MB）を導入（Gzip デコード後もチェック）
    - gzip 圧縮対応と解凍後サイズ検査（Gzip bomb 対策）
    - SSRF 対策
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート／ループバック／リンクローカル／マルチキャストであればアクセス拒否
      - リダイレクト時にもスキーム・ホスト検証を行う専用 RedirectHandler を実装
    - コンテンツ前処理（URL 除去、空白正規化）
    - 記事 ID は URL 正規化（追跡パラメータ除去）後の SHA‑256 の先頭 32 文字で生成（冪等性）
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化
    - 抽出した記事を raw_news テーブルへチャンク単位で一括 INSERT（ON CONFLICT DO NOTHING）し、INSERT RETURNING で新規挿入 ID を返却
    - 新規記事に対する銘柄コード紐付け機能（news_symbols）をバルク挿入で実装
    - 銘柄コード抽出ロジック（4桁数字候補を正規表現で抽出し、known_codes によるフィルタリング）

- スキーマ / 初期化 (kabusys.data.schema)
  - DuckDB のスキーマ定義と初期化ユーティリティを実装
    - Raw / Processed / Feature / Execution 層のテーブルを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）
    - 適切なデータ型と CHECK 制約、PRIMARY KEY / FOREIGN KEY を定義
    - パフォーマンス向けのインデックス（コード×日付やステータス検索向け）を作成
    - init_schema(db_path) でディレクトリ作成・DDL 実行を行い接続を返す（冪等）
    - get_connection(db_path) で既存 DB へ接続（スキーマは初期化しない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の骨組みを実装
    - ETLResult データクラス（実行対象日、取得数／保存数、品質問題、エラー一覧、判定ヘルパーを含む）
    - テーブル存在検査ユーティリティ、最終取得日の取得ヘルパー（get_last_price_date 等）
    - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）
    - run_prices_etl の差分更新ロジック（最終取得日から backfill_days 前を date_from に設定する等）、J‑Quants fetch と保存の接続
    - 品質チェックモジュール（quality）と連携する設計（品質問題は収集して呼び出し元で判断）

- 空モジュールのプレースホルダ
  - kabusys.execution.__init__、kabusys.strategy.__init__、kabusys.data.__init__ を配置（将来の実装用）

### セキュリティ (Security)

- 外部データ取得周りでのセキュリティ対策を追加
  - defusedxml を用いた XML パース（XML 脅威緩和）
  - SSRF 対策（リダイレクト検査、プライベートホスト拒否、スキーム検証）
  - レスポンスサイズ制限、Gzip 解凍後のサイズ検査（メモリ DoS / Zip Bomb 対策）
  - .env 読み込み時のファイル読み取りエラーを警告扱いにして安全にフォールバック

### 修正 (Fixed)

- （初版のため過去修正なし。実装時に見つかった一般的なエラーハンドリングやログ出力を追加）

### 既知の制約 / 注意点 (Known limitations)

- quality モジュールや戦略（strategy）、実際の注文実行ロジック（execution）は骨組みが中心で、詳細実装は別途実装が必要
- run_prices_etl の実装はファイル末尾で切れている（コードベースから推測したロジックの一部）。エラーハンドリング・品質チェック連携は呼び出し側での追加処理を想定
- J‑Quants のレート制限や Retry-After 解釈は実装済みだが、運用時には実トラフィックでのチューニングが必要
- news_collector の既定 RSS ソースは 1 件のみ（拡張可能）

---

## 参考

- この CHANGELOG は提供されたコードの実装内容から推測して作成しました。実際のリリースノートや履歴が存在する場合は、そちらに合わせて更新してください。