# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-17

初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 外部公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - 読み込み優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - export KEY=val 形式やクォート付き値、インラインコメントなどを考慮した .env 行パーサ実装。
  - OS 環境変数を保護する protected ロジック、override オプションをサポート。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等の取得メソッドを提供。
  - 必須環境変数未設定時は明確な例外メッセージを投げる _require() 実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能: ID トークン取得（get_id_token）、ページネーション対応での日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）取得。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）で API レート制限を遵守。
  - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象に設定。429 の場合は Retry-After を優先。
  - 401 受信時は自動で ID トークンを一度リフレッシュして再試行する仕組み（無限再帰防止）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供し、ON CONFLICT DO UPDATE により冪等保存を実現。
  - データ取得時刻（fetched_at）を UTC タイムスタンプで保存して Look-ahead Bias を抑制。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値を安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得・パース（fetch_rss）と raw_news テーブルへの冪等保存（save_raw_news）を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - HTTP リダイレクト時にスキーム検証およびホストのプライベートアドレス判定を行うカスタムリダイレクトハンドラ（SSRF 防止）。
    - URL スキームは http/https のみ許可。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を越える場合は取得を中止（gzip 解凍後も検査）。
    - User-Agent と圧縮ヘッダ対応（gzip）。
  - 記事 ID は URL 正規化（トラッキングパラメータ除去、キーでソート、フラグメント除去 等）後の SHA-256 ハッシュ先頭 32 文字で生成し、冪等性を担保。
  - トラッキングパラメータ（utm_*, fbclid, gclid, ref_, _ga）除去機能を実装。
  - 保存ロジック:
    - save_raw_news は INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事 ID のリストを返す（チャンク分割・1トランザクション）。
    - news_symbols（記事と銘柄コードの紐付け）を一括挿入する _save_news_symbols_bulk / save_news_symbols を実装し、INSERT ... RETURNING で挿入数を正確に取得。
  - 銘柄コード抽出（extract_stock_codes）: 正規表現による 4 桁数字抽出と既知コード集合によるフィルタリングを実装。
  - run_news_collection により複数ソースを順次処理し、各ソースの失敗は他ソースに影響させない堅牢なジョブ実行を提供。
  - デフォルト RSS ソースとして Yahoo ニュース（businessカテゴリ）を設定。

- DuckDB スキーマ定義および初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を付与。
  - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) 関数を実装し、親ディレクトリ自動作成・DDL 実行・インデックス作成を行い、初期化済みの DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を導入し、ETL の実行結果（取得件数／保存件数／品質問題／エラー等）を構造化して返却可能。
  - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 市場カレンダーに基づいて非営業日を直近営業日に調整する _adjust_to_trading_day を実装。
  - run_prices_etl（差分更新ロジック、バックフィル日数による後出し修正吸収、fetch→save の流れ）を部分実装。J-Quants クライアントとの注入可能な id_token によりテスト容易性を考慮。
  - デフォルトの最小データ取得開始日やカレンダー先読み日数、バックフィル日数等の定数を定義。

### Security / Reliability
- API クライアント・RSS 収集において、レート制御、リトライ、サイズ上限、XML パースの安全化、SSRF 対策などの堅牢性設計を導入。
- データベース保存は冪等性を重視（ON CONFLICT の使用や PRIMARY KEY 設計）し、トランザクションで整合性を確保。

### Internal / その他
- 各種ユーティリティ（日時パース、URL 正規化、テキスト前処理、数値変換）を実装して上位ロジックで再利用可能に。
- ロギングを各所に配置し、運用時の可観測性を確保（info/warning/exception の使い分け）。

## 既知の制限 / 今後の改善候補
- run_prices_etl の先頭部分は実装済みだが、ファイル末尾で return が途中で終わっているなど一部未完の箇所が見られる（実際のフロー完了処理や ETLResult への組み込みなどを続けて実装する必要がある）。
- strategy / execution / monitoring パッケージはパッケージ階層として存在するが、実装は未追加（プレースホルダ）。
- テストやモック（HTTP 呼び出し、DuckDB を用いた統合テスト）の整備が今後必要。

---

この CHANGELOG はコードベースから推測してまとめた内容です。実際のリリースノート作成時は、実行テスト結果や追加の変更履歴（ドキュメント・依存ライブラリ等）を反映してください。