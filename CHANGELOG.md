# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠します。フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォームのコアライブラリを追加しました。主な追加内容は以下のとおりです。

### Added
- パッケージ基本情報
  - src/kabusys/__init__.py にパッケージ名とバージョン（0.1.0）を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local ファイルおよび環境変数からの設定ロードを自動化（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env 解析: `export KEY=val` 形式、シングル/ダブルクォートやバックスラッシュエスケープ、インラインコメント処理に対応。
    - 上書き挙動: OS 環境変数を保護する protected 機構（`.env.local` は上書きモード）。
    - Settings クラスを公開（J-Quants / kabuステーション / Slack / DB パス / ログ・環境設定等のプロパティを提供）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。必須値が欠けている場合は ValueError を発生。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - 冪等での DuckDB 保存を支援する save_* 関数（ON CONFLICT DO UPDATE を使用）。
    - リトライ戦略: 指数バックオフ（最大3回）、ステータス 408/429/5xx にリトライ、429 の場合は Retry-After を考慮。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して再試行（無限再帰回避）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - JSON パース失敗やネットワークエラーに対する適切なエラーハンドリング。
    - 型変換ユーティリティ `_to_float`, `_to_int`（不整合データ時に安全に None を返す）。
    - モジュールレベルの id_token キャッシュを共有しページネーション間で利用。

- RSS ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と raw_news への保存機能。
    - セキュリティ対策:
      - defusedxml を使用した XML パース（XML Bomb 等対策）。
      - SSRF 防止: リダイレクト時にスキーム検証・プライベートアドレス検査を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。取得前のホスト事前検証も実施。
      - 許容スキームは http/https のみ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）や gzip 解凍後のサイズチェックで DoS を緩和。
      - URL 正規化でトラッキングパラメータ（utm_* 等）を除去。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去・空白正規化）と RSS pubDate の堅牢なパース（タイムゾーン処理）。
    - DuckDB への保存:
      - save_raw_news: チャンク挿入・トランザクション、INSERT ... RETURNING により実際に挿入された記事IDを返却（ON CONFLICT DO NOTHING）。
      - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けのバルク挿入（重複除去、チャンク、トランザクション、RETURNING を使用）。
    - 銘柄コード抽出ロジック（4桁数字の抽出と known_codes による検証）。
    - run_news_collection: 複数ソースを独立して処理し、エラーが発生しても他ソースは継続する設計。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution レイヤーのテーブル DDL を定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックスを定義し、頻出クエリに備えるインデックス群を作成。
    - init_schema(db_path) でディレクトリ作成（必要時）と DDL 実行による初期化（冪等）。
    - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass による実行結果の表現（取得数、保存数、品質問題、エラー一覧など）。
    - 差分更新ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を提供。
    - 市場カレンダーを利用した営業日調整ヘルパー `_adjust_to_trading_day`（最大30日遡る）。
    - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days の再取得で後出し修正を吸収）。デフォルトの backfill_days=3。初回は _MIN_DATA_DATE（2017-01-01）から取得。
    - ETL の設計方針として、データ品質チェック（quality モジュール）を呼び出し側が評価できる形で結果を返す（Fail-Fast ではない）。

- パッケージ構成
  - data/、strategy/、execution/、monitoring/ のモジュール構成を用意（strategy と execution には __init__.py のプレースホルダあり）。

### Security
- RSS 取得における SSRF 対策と XML パースの安全化（defusedxml の採用、プライベート IP 検査、スキーム制限、リダイレクト時の事前検査）。
- HTTP レスポンス読み込み上限の導入（MAX_RESPONSE_BYTES=10MB）によりメモリ DoS を軽減。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

---

注記:
- 各 API（J-Quants / kabu）利用には環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）の設定が必要です。Settings で必須チェックを行います。
- DuckDB の初期化は init_schema() を利用してください。":memory:" を渡すことでインメモリ DB を使用可能です。
- news_collector と jquants_client の一部関数はネットワーク I/O を伴うため、ユニットテストでは該当箇所をモック可能な設計になっています（例: _urlopen, id_token 注入等）。

今後の予定（例）
- quality モジュールの実装と ETL 統合、戦略層（strategy）・実行層（execution）の実装強化、監視・アラート（monitoring）との連携を予定しています。