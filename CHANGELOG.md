# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/kabusys 以下）の実装内容から推測して作成した変更履歴です。

全般
- 初期バージョン: 0.1.0（初期実装・概念実装を含む）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群の初期実装を追加。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイントを追加 (src/kabusys/__init__.py)。モジュール公開: data, strategy, execution, monitoring。
  - パッケージバージョンを "0.1.0" に設定。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出ロジックを実装 (.git または pyproject.toml を基準) — ワーキングディレクトリに依存しない自動ロード。
  - .env パース機能を追加:
    - export KEY=val 形式対応、クォート付き値のエスケープ処理、インラインコメントの扱い。
    - override / protected をサポートする .env ファイルのロード。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を実装（テスト用）。
  - 必須環境変数取得ヘルパー _require を導入 (必要なキーがない場合に ValueError)。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で提供（J-Quants、kabuステーション、Slack、DBパス、環境判定、ログレベル検証など）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得機能を実装:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ (fetch_financial_statements)
    - 市場カレンダー (fetch_market_calendar)
  - 認証ヘルパー get_id_token を実装（リフレッシュトークン → IDトークン）。
  - HTTP リクエストユーティリティ _request を実装:
    - APIレート制限（120 req/min）に合わせた固定間隔スロットリング（_RateLimiter）。
    - リトライ（指数バックオフ、最大3回、408/429/>=500 をリトライ対象）。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）と再試行。
    - JSON デコードエラーの明確な例外化。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar — ON CONFLICT DO UPDATE を用いた上書き（冪等性）。
  - データ変換ユーティリティ _to_float / _to_int を実装（安全な型変換）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集機能を実装（fetch_rss, run_news_collection）。
  - セキュリティ対策・堅牢性:
    - defusedxml による XML パース（XML Bomb 等を防ぐ）。
    - リダイレクト時の事前検証および SSRF を防ぐハンドラ (_SSRFBlockRedirectHandler)。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検査（_is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を設定しての取得。
  - フィード処理機能:
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）と記事ID生成 (SHA-256 の先頭32文字)。
    - テキスト前処理（URL除去、空白正規化）。
    - 公開日時のパース（RFC2822 対応、失敗時は現在時刻で代替）。
    - raw_news テーブルへ冪等保存（save_raw_news: INSERT ... ON CONFLICT DO NOTHING、チャンク挿入、トランザクション制御、INSERT ... RETURNING による挿入ID取得）。
    - news_symbols の一括保存（重複除去、チャンク挿入、トランザクション）。
    - 記事本文からの銘柄コード抽出（4桁数字、known_codes によるフィルタ）。
    - デフォルトソースとして Yahoo Finance のビジネスRSS を登録（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - DataPlatform の3層構造を反映する DuckDB テーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）やデータ型を定義。
  - パフォーマンス向上のためのインデックスを追加（頻出クエリ向け）。
  - init_schema(db_path) でディレクトリ自動作成 → テーブル生成（冪等）を行うユーティリティを実装。
  - get_connection(db_path) を提供（既存DBへの接続）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計に基づくパイプライン基盤を実装:
    - ETLResult データクラス（結果・品質問題・エラー集約、has_errors / has_quality_errors プロパティ、to_dict）。
    - テーブル存在チェック、最大日付取得ユーティリティ（差分取得ヘルパー）。
    - market_calendar を用いた営業日調整ヘルパー (_adjust_to_trading_day)。
    - 差分更新用ヘルパー関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - run_prices_etl の骨格実装:
      - 差分算出（last date と backfill を考慮）、J-Quants からの取得と保存呼び出し（fetch_daily_quotes / save_daily_quotes）を実装（差分ETLフローの基礎）。
  - 取得開始日のデフォルト、カレンダーの先読み、バックフィル日数のデフォルトなど運用方針を反映。

### セキュリティ (Security)
- RSS の XML パースに defusedxml を採用し XML 攻撃に対処。
- RSS フェッチで SSRF を低減するためにリダイレクト検査、ホストIP検査、スキーム検証を実装。
- .env 読み込みで OS 環境変数を保護する protected 機構を実装。

### パフォーマンス / 運用 (Performance / Ops)
- J-Quants API 呼び出しで固定間隔スロットリングを実装し API レート制限を順守。
- リクエストのリトライ（指数バックオフ）を実装しネットワークの揺らぎに耐性を持たせた。
- DuckDB へのバルク/チャンク挿入（チャンクサイズ制御）とトランザクション利用により挿入コストを削減。
- スキーマに用途別インデックスを追加し頻出クエリの高速化を図った。

### 既知の問題 (Known issues)
- run_prices_etl の実装が途中のように見える箇所があります（ファイル末尾での戻り値が未完成）。ETL の戻り値やエラー集約の最終整理が必要な可能性があります。
- まだユニットテストや統合テストに関する実装・カバレッジ情報は含まれていません（テストの整備が推奨されます）。
- strategy / execution / monitoring のサブモジュールは空の __init__.py が存在するのみで、発注ロジックや監視機能は今後の実装対象です。

### 開発上のメモ
- .env のパースは多くのケース（クォート、エスケープ、インラインコメント、export キーワード）に対応しているため、運用での環境変数管理が柔軟。
- ニュース記事ID は URL 正規化後のハッシュを採用しており、トラッキングパラメータ変動による重複登録を抑止する設計。
- DuckDB スキーマは外部キー・制約を豊富に定義しており、データ整合性と後続処理（Feature / Execution 層）を意識した構造。

---

将来的なリリースでは、以下を含めることが考えられます:
- run_prices_etl の完成・テスト、各種 ETL ジョブ（financials / market calendar / news）の連携処理の追加
- strategy / execution の実装（シグナル生成から注文送信・約定処理まで）
- 監視 (monitoring) と通知（Slack 等）の統合
- 単体テスト・統合テストの追加、および CI/CD 設定

（このCHANGELOGはソースコードの実装内容から推測して作成しています。実際のリリースノートはリリース時の変更差分に基づいて更新してください。）