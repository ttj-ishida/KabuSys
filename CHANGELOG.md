# CHANGELOG

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、記載内容は提供されたコードベースから推測してまとめたリリースノートです。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加・実装点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（空の __init__ を含むモジュールスタブを作成）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定値を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト用）。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - コメント判定の挙動を細かく制御。
  - Settings クラスにより安全に環境変数を取得:
    - 必須項目チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - デフォルト値（KABU_API_BASE_URL, DB パス等）。
    - env と log_level の値検証（許容値チェック）。
    - is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得機能を実装。
  - 設計方針・機能:
    - API レート制限対策（固定間隔スロットリング）: 120 req/min を守る RateLimiter 実装。
    - リトライロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx はリトライ対象。
    - 401 受信時はリフレッシュトークンから id_token を自動でリフレッシュして 1 回だけ再試行。
    - ページネーション対応（pagination_key を扱い重複防止）。
    - fetched_at を UTC で記録して Look-ahead bias を緩和。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装。
  - 型変換ユーティリティ: _to_float, _to_int（空/不正値に安全に対応）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存する一連の実装。
  - 設計方針・機能:
    - デフォルト RSS ソース（yahoo_finance）を用意。
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - HTTP レスポンスの最大バイト数制限（MAX_RESPONSE_BYTES = 10 MiB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
    - リダイレクト時／最終 URL に対する SSRF 対策:
      - 許可スキームは http/https のみ。
      - プライベート/ループバック/リンクローカル/マルチキャスト IP を検出してアクセス拒否。
      - リダイレクトを検査するカスタムハンドラ _SSRFBlockRedirectHandler を導入。
    - URL 正規化（トラッキングパラメータ除去、クエリをキー順でソート、スキーム/ホスト小文字化、フラグメント削除）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で一意化・冪等化。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB への保存はトランザクションでまとめ、INSERT ... RETURNING により実際に挿入された ID を取得。
    - 銘柄コード抽出（4 桁数字パターン）と news_symbols テーブルへの紐付け（バルク挿入、重複除去）。
    - 外部に公開されたユーティリティ関数:
      - fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes 等。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義を実装。
  - 主要テーブル（例）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与しデータ整合性を強化。
  - 検索パフォーマンス向上のためのインデックス群を定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成および DDL 実行（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない点を明記）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（差分取得）と保存のためのヘルパー群を実装。
  - 機能:
    - DB の最終取得日を取得するユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 非営業日の調整ロジック（_adjust_to_trading_day）。
    - ETLResult データクラスにより ETL の結果・品質問題・エラーを集約（to_dict で可視化可能）。
    - run_prices_etl 実装（差分更新、backfill_days による再取得、jq.fetch_daily_quotes → jq.save_daily_quotes の流れ）。
    - 設計方針として品質チェック（quality モジュール）を呼び出す前提とし、Fail-Fast ではなく全件収集して呼び出し元に判断を委ねる設計（quality 関連は別モジュール参照）。

- ロギング
  - 各モジュールで logger を使用して重要イベント・警告を出力（取得件数、保存件数、パース失敗、サイズ超過、トランザクション失敗等を記録）。

### 変更 (Changed)
- 初期リリースのため該当なし（新規実装のみ）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- RSS 処理における複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキームチェック・プライベート IP ブロック・リダイレクト検査）。
  - レスポンスサイズ制限によるメモリ DoS / Gzip bomb 対策。
  - .env パーサーでのエスケープ処理の改善により誤設定を低減。

### 既知の制限・注意点 (Known issues / Notes)
- pipeline.run_prices_etl 等の ETL 関数群は品質チェックモジュール（quality）や一部の連携ロジックを想定して実装されており、運用時には quality モジュール・スケジューラ・認証トークン管理等の周辺実装が必要です。
- strategy, execution, monitoring パッケージはインターフェースの土台（スタブ）を用意しています。実運用のための戦略ロジックや注文実行エンジンは今後実装する想定です。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特定の配置環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御してください。

---

（以降のリリースでは、互換性の有無、追加/変更/削除された API、マイグレーション手順などを明記してください。）