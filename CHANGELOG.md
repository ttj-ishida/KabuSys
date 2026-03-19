# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングに従います。

なお、以下の内容はコードベースから推測して記載したものであり、実装方針・仕様の要点をまとめたものです。

## [Unreleased]


## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主要な追加点は下記のとおりです。

### Added
- パッケージ構成
  - パッケージ `kabusys` の基本構造を追加。
  - サブパッケージ: `data`, `strategy`, `execution`, `research`, `monitoring` を公開エントリとして定義。

- バージョン情報
  - `kabusys.__version__ = "0.1.0"` を追加。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの探索は `.git` または `pyproject.toml` を基準として行い、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local (> .env)。既存 OS 環境変数は保護（上書き防止）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - .env ファイルのパースは次の特徴を持つ:
    - コメント行 / export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに配慮。
  - Settings クラスを提供（単一インスタンス `settings` をエクスポート）。
    - 必須設定の取得 (`_require`): 未設定時は ValueError を発生。
    - サポート項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）。
    - ヘルパー: is_live / is_paper / is_dev。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回）を実装。HTTP 408 / 429 / 5xx 系に対するリトライを行う。
    - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして 1 回リトライ（リフレッシュ中の再帰を防ぐ仕組みあり）。
    - ページネーション対応（pagination_key を使った繰り返し取得）。
    - Look-ahead-bias 対策として取得時刻（UTC）を `fetched_at` に記録。
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes → raw_prices に INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements → raw_financials に INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar → market_calendar に INSERT ... ON CONFLICT DO UPDATE
  - 型変換ユーティリティ:
    - _to_float, _to_int（不正値や空文字を安全に None 化、float系文字列からの int 変換の扱いに注意）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して DuckDB に保存するワークフローを実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML Bomb 等の防御）。
      - SSRF 対策: リダイレクト前後でスキーム/ホスト検証（_SSRFBlockRedirectHandler, _is_private_host）。
      - 許可スキームは http/https のみ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化と記事 ID 生成:
      - トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、スキーム/ホスト小文字化、フラグメント除去、クエリキーソート。
      - 正規化 URL の SHA-256 ハッシュ先頭32文字を記事IDとして採用（冪等性確保）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄抽出:
      - 4桁の数字パターンから known_codes に存在するものだけを抽出。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された ID を返却。チャンク分割・一括挿入を実装（トランザクションでまとめる）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク挿入で実装（RETURNING を用いて挿入件数を数える）。
    - run_news_collection: 複数ソースを順次処理し、ソース単位でエラーハンドリング（1ソース失敗しても継続）し、known_codes が与えられれば銘柄紐付けまで実行。

- リサーチ（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日からの複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily を参照して計算。ホライズンは 1〜252 の整数制約あり。
    - calc_ic: スピアマン順位相関（IC）を計算。ペアが3件未満、分散が0の場合は None を返す。ランク計算は同順位の平均ランクを用いる。
    - rank: 同順位は平均ランク扱い、丸め誤差対策のため round(v, 12) を用いて ties を検出。
    - factor_summary: 各カラムについて count/mean/std/min/max/median を計算（None と非数値を除外）。
  - factor_research モジュール:
    - calc_momentum:
      - mom_1m/mom_3m/mom_6m（約1/3/6か月リターン）、ma200_dev（200日移動平均乖離）を計算。必要なデータ不足時は None。
    - calc_volatility:
      - atr_20（20日 ATR平均）、atr_pct（ATR/価格）、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均）を計算。high/low/prev_close が NULL の場合の true_range 処理に注意。
    - calc_value:
      - raw_financials から target_date 以前の最新財務を取得し、per（株価/EPS）、roe を出力。EPS が 0/欠損の場合は per を None。
  - 研究 API のエクスポート:
    - kabusys.research.__init__ で主要ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw Layer のテーブル定義を追加（CREATE TABLE IF NOT EXISTS 文）:
    - raw_prices, raw_financials, raw_news, raw_executions（途中まで定義が含まれる）
  - スキーマ定義は DataSchema.md に基づく層構造（Raw / Processed / Feature / Execution）を想定。

### Security
- ニュース収集における SSRF、XML 注入、Gzip bomb、巨大レスポンス攻撃などに対する複数の防御を実装。
- 外部 API 呼び出し（J-Quants）では ID トークン管理と自動リフレッシュ、レート制限とリトライ制御を実装。

### Notes / Usage
- いくつかの環境変数は必須（settings のプロパティ参照）。未設定の場合は ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- DuckDB の所定のテーブル（prices_daily, raw_financials, raw_prices, raw_news, market_calendar 等）が存在することを前提に動作します。スキーマ初期化は `kabusys.data.schema` の DDL を参考に行ってください。
- news_collector.run_news_collection / fetch_rss はネットワーク I/O を伴うため、テスト時は `_urlopen` やネットワーク呼び出しをモック可能です。
- jquants_client の _MIN_INTERVAL_SEC / RATE_LIMIT / RETRY 設定は定数で定義されているため、将来変更可能。

### Known limitations / TODO
- strategy / execution サブパッケージは空の初期プレースホルダ（実装は今後）。
- 一部のテーブル定義（raw_executions など）がファイル内で途中まで記載されており、完全な DDL 定義は追加実装が必要。
- 外部依存ライブラリ（duckdb, defusedxml 等）が稼働環境に必要。
- 単体テスト・統合テストはコードから想定される設計（自動 env ロードの無効化フラグ、ネットワークモックの差替え等）を元に整備することを推奨。

---

（以上）