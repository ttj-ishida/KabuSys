# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
安定したリリースバージョンのみを記載しています。

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基盤的なモジュールを実装しました。主な追加点は以下の通りです。

### 追加
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサの実装: export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応。
    - Settings クラスを提供し、必須環境変数取得（_require）・既定値・バリデーション（KABUSYS_ENV, LOG_LEVEL）・便利プロパティ（is_live 等）を実装。
    - 必須変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得用 API クライアントを実装。
    - レート制御: 固定間隔スロットリングで 120 req/min (_RateLimiter)。
    - リトライ: 指数バックオフ（最大 3 回）、対象ステータス 408/429/5xx。429 の場合は Retry-After ヘッダを優先。
    - 認証: refresh_token から id_token を取得する get_id_token、HTTP 401 受信時に自動リフレッシュして 1 回だけ再試行。
    - ページネーション対応（pagination_key を追跡）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を考慮し ON CONFLICT DO UPDATE を使用。
    - 取得時刻（fetched_at）は UTC で記録（Look-ahead Bias の追跡に対応）。
    - 型変換ユーティリティ _to_float / _to_int を提供（不正値や空値の安全な扱い）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を取得して raw_news テーブルに保存する機能を実装。
    - 設計上の特徴:
      - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と SHA-256（先頭32文字）に基づく記事ID生成で冪等性を確保。
      - defusedxml を使用して XML-Bomb 等を防御。
      - SSRF 対策: URL スキーム制限（http/https のみ）、リダイレクト時の事前検証ハンドラ、ホストのプライベートアドレス判定。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - コンテンツ前処理（URL 除去、空白正規化）。
      - DB への保存はトランザクション内でチャンク化して実行。INSERT ... RETURNING を使い、実際に挿入された記事IDや件数を正確に返却。
      - 銘柄コード抽出（4桁数字）と news_symbols への紐付け処理（重複除去・バルク挿入）。
    - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを設定。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - DataPlatform に基づく 3 層＋実行レイヤのテーブル定義を実装:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに妥当性制約（CHECK、PRIMARY/FOREIGN KEY 等）を付与。
    - 頻出クエリ向けインデックスを定義。
    - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成（冪等）。get_connection() で既存DBへ接続。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETL の設計ドキュメントに基づく差分 ETL 基盤を実装（ETLResult データクラス、差分計算、バックフィル、品質チェック連携フック）。
    - 市場カレンダー先読み日数や差分更新のデフォルト（最終取得日の backfill）などの定数を定義。
    - DB の最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）、テーブル存在チェック、営業日調整ヘルパーを提供。
    - run_prices_etl の骨格を実装（差分計算→jquants_client.fetch/save を呼び出すフロー）。※ 一部コードは続きあり（初回実装の段階）。

- パッケージ構成プレースホルダ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を追加（将来的な拡張のためのモジュール構成）。

### 改善 / 設計メモ
- 各種 I/O に対する堅牢性を重視（ネットワーク/HTTP のリトライ、XML の安全パース、SSRF 対策、レスポンスサイズ制限）。
- DuckDB を中心とした冪等な永続化戦略（ON CONFLICT / INSERT ... RETURNING / トランザクションチャンク）を採用。
- テスト容易性を考慮し、id_token の注入や _urlopen のモックポイントなどを用意。
- ログ出力を充実させ、取得件数やスキップ件数、トランザクション失敗時のロールバックを記録。

### 既知の制約 / 今後の作業
- pipeline.run_prices_etl の実装は本リリースで基本フローを実装済みですが、品質チェックモジュール（kab usys.data.quality）の統合や run_financials_etl/run_calendar_etl 等の完全実装・テストが今後の作業です。
- strategy / execution / monitoring の具体的なロジックは未実装（モジュールプレースホルダのみ）。

### セキュリティ
- RSS XML のパースに defusedxml を使用。
- SSRF 対策: スキーム制限、リダイレクト先の事前検査、プライベートアドレス判定（直接 IP および DNS 解決した結果の検査）。
- レスポンスサイズの上限設定によりメモリ DoS を低減。

---

過去の互換性に影響しうる破壊的変更は本初回リリース時点ではありません。導入時は settings クラスで要求される必須環境変数と DuckDB スキーマ初期化（init_schema）を確認してください。