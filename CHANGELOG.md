# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティック バージョニングを採用します。  
このファイルは、リポジトリのコードから推測して作成しています。

## [0.1.0] - 2026-03-18

### 追加
- 初期リリース: KabuSys 日本株自動売買システムのコア機能群を実装。
- パッケージ構成:
  - kabusys (トップレベル)
  - サブパッケージ: data, strategy, execution, monitoring（空の __init__ を含む）
- 環境設定 / ロード:
  - 環境変数管理モジュールを実装（kabusys.config）。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索し、配布後も安定して .env を読み込むよう設計。
  - .env 自動読み込みのサポート: 読み込み優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テスト用途）。
  - .env パーサーは以下に対応:
    - コメント行 / 空行のスキップ
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント認識（直前が空白/タブのみ）
  - Settings クラスを提供。必須環境変数の取得（J-Quants, kabu API, Slack, DB パス 等）と値検証（環境名、ログレベルの許容値など）を実装。
- J-Quants クライアント（kabusys.data.jquants_client）:
  - API 呼び出しのための統合クライアントを実装。
  - レート制限（120 req/min）を固定間隔スロットリングで強制する RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。対象ステータスは 408/429/5xx。
  - 401 受信時はリフレッシュトークンで自動的に ID トークン再取得して 1 回だけリトライするロジックを実装（再帰防止のため allow_refresh 制御あり）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）は UTC ISO フォーマットで保存して Look-ahead Bias を防止。
  - モジュールレベルで ID トークンキャッシュを保持し、ページネーション間で使い回すことで余分な認証呼び出しを削減。
- ニュース収集モジュール（kabusys.data.news_collector）:
  - RSS フィードから記事を収集し、前処理・DB 保存・銘柄紐付けを行うフローを実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等対策）
    - リダイレクト時にスキーム検証・プライベートアドレス検出を行うカスタム HTTPRedirectHandler（SSRF 対策）
    - URL スキームは http/https のみ許可
    - レスポンス受信サイズ上限（10 MB）と gzip 解凍後のサイズ検査（Gzip-bomb 対策）
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、クエリソート、フラグメント削除。
  - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字を使用して冪等性を確保。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事 ID を返却（トランザクション内で処理）。
    - save_news_symbols, _save_news_symbols_bulk: news_symbols テーブルへ記事と銘柄コードの紐付けを一括挿入（ON CONFLICT で重複をスキップ、INSERT ... RETURNING により正確な挿入数を算出）。
  - 銘柄抽出ロジック: 4 桁数字パターンを known_codes セットでフィルタして抽出（重複排除）。
  - run_news_collection: 複数ソースから独立して収集し、失敗したソースは無視して継続する堅牢なジョブ機能を実装。デフォルトで Yahoo Finance のビジネス RSS を使用。
- DuckDB スキーマ（kabusys.data.schema）:
  - DataPlatform の設計に基づく 3 層＋実行層のテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を明示的に定義。
  - 頻出クエリ向けのインデックスを作成する DDL を用意。
  - init_schema(db_path) 関数で DB ファイルの親ディレクトリ自動作成後に全 DDL を実行してスキーマを初期化する機能を提供。get_connection() で既存 DB へ接続可能。
- ETL パイプライン（kabusys.data.pipeline）:
  - ETL の設計（差分更新、backfill、品質チェックを考慮）に基づいた骨格を実装。
  - ETLResult データクラスを実装し、実行結果・品質問題の一覧化（辞書化）をサポート。
  - 市場カレンダー補助やテーブル最終日取得等のユーティリティ関数を実装。
  - run_prices_etl を実装（差分取得ロジック、backfill_days による再取得、J-Quants からの fetch 及び save を呼び出し）。
  - 最小データ開始日、カレンダー先読み日数、デフォルトの backfill 日数等の定数を提供。

### 変更
- 該当なし（初期リリース）。

### 修正
- 該当なし（初期リリース）。

### セキュリティ
- RSS パーサーに defusedxml を使用し、XML パースにおける脆弱性対策を実施。
- ニュース収集での SSRF 対策: リダイレクト先のスキーム/ホスト検証および DNS 解決結果によるプライベート IP 判定。
- 外部 URL のスキーム制限（http/https のみ）・レスポンスサイズ制限・gzip 解凍後のサイズ検査により、DoS や Gzip-bomb を緩和。

### パフォーマンス
- J-Quants API 呼び出しでトークンキャッシュを導入し認証呼び出しを削減。
- RateLimiter による固定間隔スロットリングで API レート制限を保証。
- news_collector の DB 挿入はチャンク化して一括 INSERT を行い、トランザクションでまとめることでオーバーヘッドを低減。
- save_* 関数は冪等に設計（ON CONFLICT）され、再実行による重複を防止。

### 既知の問題 / 注意点
- run_prices_etl の戻り値:
  - ドキュメントでは (取得レコード数, 保存レコード数) のタプルを返すと記載されているが、実装の末尾が `return len(records),` のように単要素のタプル（もしくは意図せぬ値）を返しており、呼び出し側が期待する (fetched, saved) 形式と異なる可能性があります（修正が必要）。
- pipeline モジュールは骨格が実装されているが、品質チェック（quality モジュール呼び出し）などの詳細な統合は別途の実装が想定される。
- news_collector の DNS 解決失敗時は安全側（非プライベート）とみなす設計になっているが、運用要件に応じたポリシー調整を検討してください。
- 一部サブパッケージ（strategy, execution, monitoring）は初期の __init__ のみで具体的実装は未搭載。

### マイグレーション / 使用メモ
- 初回利用時は必ず init_schema(db_path) を実行して DuckDB スキーマを作成してください。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
- テスト等で .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

（本 CHANGELOG は、提供されたコードの内容を基に自動的に推測して作成しています。実際の変更履歴やリリースノートは、プロジェクトの Git 履歴やリリース手順に基づいて適宜更新してください。）