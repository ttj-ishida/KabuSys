# CHANGELOG

全ての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
リリース日付はコードベースのスナップショットから推測して設定しています。

## [Unreleased]

<!-- 当面の開発中の変更をここに記載 -->

---

## [0.1.0] - 2026-03-18

最初の公開リリース（推定）。日本株自動売買プラットフォームのコア機能群を追加。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。バージョンは 0.1.0 に設定。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（配布後も安定して動作）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメント処理等。
  - 必須設定取得用 _require() を実装（未設定時は ValueError）。
  - 有効な環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）に対する入力検証を実装。
  - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 基本 GET/POST リクエストラッパー _request()。
    - レートリミット制御（120 req/min 固定）を行う _RateLimiter。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）と 429 の Retry-After 優先処理。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止の allow_refresh フラグ）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - APIデータ取得関数:
    - fetch_daily_quotes（OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes（raw_prices テーブルへ ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブルへ ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブルへ ON CONFLICT DO UPDATE）
  - データ整形ユーティリティ: _to_float / _to_int（不正値や空値を安全に扱う）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存するモジュールを追加。
  - 設計上の主要機能:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性）。
    - XML パースに defusedxml を使用して XML Bomb 等を防御。
    - SSRF 対策:
      - URL スキームは http/https のみ許可。
      - リダイレクト先のスキームとホストを事前検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホスト名は DNS 解決してプライベート/ループバック/リンクローカル/マルチキャストを検出し拒否。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - コンテンツ前処理（URL 除去、空白正規化）。
    - DuckDB への保存はトランザクションでまとめ、チャンク(デフォルト1000件)ごとに INSERT ... RETURNING を利用して実際に挿入された ID を取得。
    - news_symbols のバルク挿入関数（重複除去、チャンク処理、ON CONFLICT DO NOTHING）。
    - 銘柄コード抽出機能（4桁数字パターンを検出し、known_codes に含まれるもののみ返す）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用スキーマ（Raw / Processed / Feature / Execution 層）を定義。
  - テーブル群（例）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックス群を定義。
  - init_schema(db_path) によりディレクトリ作成→全 DDL とインデックスを冪等的に実行して接続を返す。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の枠組みを実装:
    - ETLResult dataclass（取得件数、保存件数、品質問題、エラーの集約、ヘルパーメソッド）。
    - 差分更新ユーティリティ: テーブル存在チェック、最大日付取得（_get_max_date）。
    - 市場カレンダーヘルパー _adjust_to_trading_day（非営業日を過去方向に調整、最大30日遡り）。
    - raw_prices/raw_financials/market_calendar の最終取得日取得関数。
    - run_prices_etl: 差分取得ロジック（最終取得日 - backfill_days から再取得する default backfill_days=3）、J-Quants からの取得と保存を実行。初回ロード用の最小日付は 2017-01-01。
    - ETL は品質チェックを実行するためのフックを想定（quality モジュール参照、重大度を判定可能）。

### 変更 (Changed)
- なし（初期実装のため、既存の後方互換性に関する記載はありません）。

### 修正 (Fixed)
- なし（初期実装のため）。

### セキュリティ (Security)
- RSS パースに defusedxml を使用し XML 関連攻撃を軽減。
- RSS フェッチ時に SSRF 対策（スキーム検証、プライベートIP検出、リダイレクト時の検査）を実装。
- HTTP レスポンス上限（10MB）や gzip 解凍後のサイズチェックによりメモリ DoS / gzip bomb に備える。
- .env の読み込みでは OS 環境変数を保護する protected 機構を実装（override の制御）。

### 注意事項 / 既知の制約 (Notes)
- jquants_client のレート制限は固定で 120 req/min。アプリケーションで変更する場合は RateLimiter の挙動を調整する必要があります。
- id_token はモジュールレベルでキャッシュされ、401 時に 1 回自動リフレッシュする設計。特殊な利用では allow_refresh を適切に制御してください（無限再帰防止）。
- DuckDB への保存は SQL を直接組み立てて実行している箇所があり（INSERT 文のプレースホルダ連結など）、SQL インジェクションの影響は少ない想定だが、外部から未検証の SQL 片を流す使い方は避けてください。
- pipeline モジュールは一部機能（品質チェック連携や他の ETL ジョブの統合）が外部モジュール（quality 等）に依存します。これらのモジュールの実装状態により挙動が変わります。
- news_collector の extract_stock_codes は単純に 4 桁数字を抽出し known_codes と照合します。自然言語中の誤検出や文脈依存の絞り込みは別途改善の余地あり。

---

作成者注: 上記はリポジトリ内のソースコードを基に機能・設計意図を推測して作成した変更履歴です。実際のコミット履歴やリリース日付、マイナー/パッチの分割などはリポジトリ運用ポリシーに応じて調整してください。