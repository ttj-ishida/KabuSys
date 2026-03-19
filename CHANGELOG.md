# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
当リポジトリのバージョンはパッケージ定義 (src/kabusys/__init__.py) の __version__ を基準にしています。

## [0.1.0] - 2026-03-19

初回リリース。本バージョンで追加された主な機能・設計方針は以下のとおりです。

### 追加
- パッケージ骨組み
  - パッケージエントリポイント (src/kabusys/__init__.py) を追加。モジュール群（data, strategy, execution, monitoring）を公開。
- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得する API を提供。
  - 必須環境変数チェックを行う _require() を実装（未設定時は ValueError を送出）。
  - サポートする環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（許容値: development, paper_trading, live、デフォルト: development）
    - LOG_LEVEL（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト: INFO）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 を設定すると自動 .env ロードを無効にできる）
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して特定。
    - ロード順序: OS 環境変数 > .env.local > .env（.env.local は上書き、.env は未設定時に補完）。
    - .env のパースは Bash 風の記法をサポート（export プレフィックス、シングル/ダブルクォート、インラインコメント処理など）。
    - ファイル読み込み失敗時には警告を出す。

- データ API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - レート制限遵守のため固定間隔スロットリング (RateLimiter) を実装（デフォルト 120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 受信時は自動でリフレッシュトークンからトークンを再取得して 1 回リトライ。
    - ページネーション対応（pagination_key のループ）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
  - DuckDB 保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 挿入は冪等性を担保する ON CONFLICT … DO UPDATE を使用。
    - fetched_at（UTC ISO8601）を付与していつデータを取得したかトレース可能に。
  - 入出力ユーティリティ:
    - _to_float / _to_int 変換ユーティリティを実装。変換失敗時は None を返す。
    - saved レコード数のログ出力。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集と raw_news テーブルへの保存機能を実装。
  - セキュリティ/堅牢化:
    - defusedxml を使った XML パース（XML Bomb など対策）。
    - SSRF 対策: fetch 前にホストのプライベートアドレス判定、リダイレクト時の検査、許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入。gzip 解凍後も検査。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成し冪等性を担保。
  - フロー:
    - fetch_rss: RSS 取得・パース・記事整形（タイトル・content の前処理、pubDate のパース）を実装。
    - preprocess_text: URL 除去・空白正規化を実装。
    - save_raw_news: チャンク分割して INSERT … RETURNING により新規挿入された記事ID一覧を取得。全てを 1 トランザクションで処理。
    - news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT … RETURNING を利用）。
    - extract_stock_codes: テキストから 4 桁の銘柄コードを抽出（既知コードセットでフィルタリング）。
    - run_news_collection: 複数RSSソースを順次処理し、失敗したソースはスキップして継続。新規記事の銘柄紐付け処理を実行。
  - デフォルト RSS ソースを一件登録（Yahoo Finance ビジネスカテゴリ）。

- 研究（Research）モジュール (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得するクエリを実装。ホライズンは 1〜252 の正整数でバリデーション。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。null/非有限値・サンプル数制約（>=3）を考慮。
    - rank: 同順位は平均ランクを採用。丸め誤差対策として round(v, 12) を使用。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を標準ライブラリだけで算出。
  - factor_research.py:
    - calc_momentum: mom_1m, mom_3m, mom_6m、ma200_dev（200日移動平均乖離）を計算。ウィンドウ不足は None。
    - calc_volatility: 20日 ATR、ATR/price、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播に注意してカウントを算出。
    - calc_value: raw_financials の最新財務データ（target_date 以前）を使用して PER（EPS が 0 または NULL の場合は None）と ROE を計算。
  - 仕様:
    - 全研究関数は DuckDB 接続（prices_daily / raw_financials）を受け取り、本番口座/API にはアクセスしないことを明示。
    - 戻り値は (date, code) をキーとする dict のリスト。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw layer のテーブル DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions（raw_executions 定義はファイル末尾で継続予定）
  - スキーマは DataSchema.md に基づく3層構造を想定（Raw / Processed / Feature / Execution 層）。

- 公開 API（research パッケージ __init__）
  - calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank を __all__ で公開。

### 変更
- （初回リリースのため過去からの変更はなし）

### 修正
- （初回リリースのため過去からの修正はなし）

### セキュリティ
- news_collector にて複数の SSRF/DoS 対策を導入（プライベート IP 判定、リダイレクト検査、Content-Length/実読込上限、gzip 解凍サイズ検査、defusedxml）。

### ドキュメント/設計メモ（コード内ドキュメンテーション）
- 各モジュールに目的・設計方針・注意点を docstring とログに明記。
- Look-ahead bias 防止のため fetched_at を UTC で記録する方針を jquants_client に明示。
- DuckDB への保存は可能な限り冪等化（ON CONFLICT）して再実行可能に。

---

注意:
- 上記はソースコードから推測して記載した CHANGELOG です。実際のリリース日や追加したファイル群が将来変更される可能性があります。必要であれば、個々の関数/モジュールに対するより詳細な変更点（引数仕様、例外動作、返り値の形式）を別途出力します。