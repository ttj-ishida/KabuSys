# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
バージョン番号は semver に従います。

## [Unreleased]


## [0.1.0] - 2026-03-17
初期リリース。日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を定義 (src/kabusys/__init__.py)。
  - 公開モジュール: data, strategy, execution, monitoring を想定したパッケージ構成。

- 設定管理
  - 環境変数/設定管理モジュールを追加 (src/kabusys/config.py)。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動的に .env を検索。
  - 自動 .env 読み込み: OS 環境変数 > .env.local > .env の優先順位でロード。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: export プレフィックス、クォート内のエスケープ、コメント処理等の実装。
  - 保護機能: OS 環境変数を protected として .env の上書きを制御。
  - Settings クラス: J-Quants / kabuAPI / Slack / DB パス等のプロパティとバリデーション（KABUSYS_ENV, LOG_LEVEL 等）を提供。

- J-Quants API クライアント
  - jquants_client モジュールを追加 (src/kabusys/data/jquants_client.py)。
  - 機能:
    - 株価日足（OHLCV）, 財務データ（四半期 BS/PL）, JPX マーケットカレンダーの取得。
    - ページネーション対応。
    - レート制御: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter 実装。
    - リトライ機構: 指数バックオフ（最大 3 回）、対象ステータス 408/429/5xx。
    - 401 (Unauthorized) を受信した場合はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
    - トークンキャッシュ: モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。
  - データ保存:
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。
    - 冪等性を確保するため INSERT ... ON CONFLICT DO UPDATE を使用。
    - fetched_at に UTC タイムスタンプを付与。
  - ユーティリティ:
    - 安全な数値変換関数 _to_float / _to_int（不正値や小数切り捨ての制御）。

- ニュース収集（News Collector）
  - news_collector モジュールを追加 (src/kabusys/data/news_collector.py)。
  - 機能:
    - RSS フィード取得（デフォルトソース: Yahoo Finance のビジネスカテゴリ）。
    - defusedxml を用いた XML パースで XML-Bomb 等の攻撃対策。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10 MB）と Gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - SSRF 対策:
      - HTTP リダイレクト毎にスキーム検証とホストのプライベートアドレス判定を行うカスタムリダイレクトハンドラ。
      - URL スキームは http/https のみ許可。プライベート IP / ループバック / リンクローカル / マルチキャスト等はブロック。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid, gclid, ref_, _ga 等）。
    - 記事ID は正規化 URL の SHA-256 ハッシュから 先頭32文字を採用して冪等性を担保。
    - テキスト前処理: URL 除去、空白正規化。
    - DB 保存:
      - raw_news テーブルへチャンク単位で INSERT と INSERT ... RETURNING を使用して新規挿入 ID を正確に取得。
      - news_symbols による銘柄紐付けの一括保存（重複除去、トランザクション制御）。
    - 銘柄コード抽出:
      - 正規表現で 4 桁数字候補を抽出し、known_codes でフィルタ（重複除去）。
    - 統合ジョブ run_news_collection: 各ソースごとに個別に例外処理を行い、1 ソース失敗でも他ソースは継続。known_codes が与えられれば新規挿入記事に対して銘柄紐付けを行う。

- DuckDB スキーマ定義
  - schema モジュールを追加 (src/kabusys/data/schema.py)。
  - DataPlatform に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、CHECK、PRIMARY KEY、FOREIGN KEY を設定。
  - よく使うクエリに対するインデックスを定義（例: code×date の検索、ステータス検索など）。
  - init_schema(db_path) 関数でディレクトリ作成（必要なら）→ 全 DDL を実行してテーブル・インデックスを作成（冪等）。
  - get_connection(db_path) 関数で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン
  - pipeline モジュールを追加 (src/kabusys/data/pipeline.py)。
  - 機能:
    - 差分更新の概念を導入（DB の最終取得日を参照して未取得範囲のみ取得）。
    - backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収（デフォルト 3 日）。
    - calendar の先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）。
    - ETLResult データクラス: ETL 実行結果、品質問題（quality モジュール想定の QualityIssue）、エラーリストを保持。品質エラー検出判定用プロパティを提供。
    - DB 上の最終日取得ユーティリティ（get_last_price_date 等）と営業日調整ヘルパー（_adjust_to_trading_day）。
    - run_prices_etl の実装（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes → 結果ログ）。差分ロジック、日付バリデーションを内包。

### Security
- RSS/XML 関連のセキュリティ強化:
  - defusedxml を使用して XML パースを安全化。
  - レスポンスサイズ制限や Gzip 解凍後のサイズチェックでメモリ DoS／圧縮爆弾に対処。
  - SSRF 対策としてリダイレクト検査とプライベートアドレス検出を実装。
- 環境変数の扱い:
  - OS 環境変数を保護する protected 処理により、.env からの意図しない上書きを防止。

### Notes
- quality モジュールや strategy / execution / monitoring の細部実装は本リリースでは限定的（モジュールのプレースホルダや参照は存在）。
- DB スキーマや保存処理は DuckDB を前提とする。テーブルの整合性や制約はスキーマ定義に依存。
- J-Quants API の認証にはリフレッシュトークンが必要（settings.jquants_refresh_token を参照）。
- news_collector の network IO 部分はテスト用に _urlopen をモックし差し替え可能な設計。

### Breaking Changes
- 初回リリースのため該当なし。

---

（将来のリリースでは各モジュールの細かな挙動改善、エラーハンドリングの強化、テストカバレッジの拡充、strategy/execution/monitoring の実装追加を予定）