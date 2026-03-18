CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

フォーマット: 日本語。リリースはセマンティックバージョニングに従います。

Unreleased
----------

（現時点の開発中の変更はここに記載します。不要であれば空のままにしてください。）

0.1.0 - 2026-03-18
-----------------

初回公開リリース。

Added
- パッケージ基盤
  - pakage: kabusys 初期モジュールを追加。トップレベルで data, strategy, execution, monitoring をエクスポート。
  - バージョン: __version__ = "0.1.0" を設定。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを導入。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を起点に探索（cwd に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用）。
  - .env パーサを実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理に対応）。
  - 環境設定ラッパ Settings を導入。主要プロパティ:
    - jquants_refresh_token (必須)
    - kabu_api_password (必須)
    - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token / slack_channel_id (必須)
    - duckdb_path（デフォルト: data/kabusys.duckdb）
    - sqlite_path（デフォルト: data/monitoring.db）
    - env (development|paper_trading|live の検証)
    - log_level (DEBUG/INFO/WARNING/ERROR/CRITICAL の検証)
    - ユーティリティ: is_live / is_paper / is_dev

- Data モジュール: J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能: 日足・財務・マーケットカレンダーの取得と DuckDB への保存ユーティリティを実装。
  - レート制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - 再試行ロジック: 指数バックオフ（最大3回）、HTTP 408/429/5xx をリトライ対象に。
  - 401 処理: 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライ。
  - ページネーション対応: pagination_key を使用した全件フェッチ。
  - 保存関数（冪等）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - データ型変換ユーティリティ: _to_float / _to_int（厳密な変換ルールを採用）。
  - Look-ahead-bias 対策: fetched_at を UTC で記録。

- Data モジュール: ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得と raw_news/news_symbols への冪等保存機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対応: リダイレクト先のスキーム検査とプライベートアドレス検出（DNS 解決時の A/AAAA 全レコード検査）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - _SSRFBlockRedirectHandler によるリダイレクト時の事前検査。
  - フィードの前処理:
    - URL 除去、空白正規化（preprocess_text）
    - トラッキングパラメータ削除と URL 正規化（_normalize_url）
    - 記事 ID は正規化 URL の SHA-256 先頭32文字（冪等性保証）
    - pubDate のパース（タイムゾーン考慮、パース不能時はログ出力して現在時刻で代替）
  - DB 側の効率化:
    - INSERT ... RETURNING を使用して実際に挿入された ID を正確に取得。
    - バルク挿入のチャンク分割（_INSERT_CHUNK_SIZE）。
    - トランザクションを使用して一括挿入・ロールバック対応。
  - 銘柄抽出:
    - 正規表現ベースで 4 桁の銘柄コードを抽出し、known_codes セットで検査して重複排除して返す。
  - 統合ジョブ run_news_collection を提供（ソースごとに個別にエラーハンドリング）。

- Data スキーマ (kabusys.data.schema)
  - DuckDB 用のスキーマ DDL を定義（Raw / Processed / Feature / Execution 層の設計方針を明記）。
  - raw_prices / raw_financials / raw_news / raw_executions 等のテーブル定義を含む（CHECK 制約や PK 指定あり）。

- Research モジュール (kabusys.research)
  - 主要関数をエクスポート:
    - calc_momentum: 1M/3M/6M リターン、MA200乖離を計算（prices_daily のみ参照）
    - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率を計算
    - calc_value: PER, ROE を raw_financials と prices_daily から計算
    - calc_forward_returns: 指定日の将来リターン（複数ホライズン）を計算
    - calc_ic: スピアマンランク相関（IC）を計算（欠損・ties に対応）
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクを返すランク関数（丸め誤差対策で round を使用）
  - 設計方針強調:
    - DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（外部 API・発注操作なし）
    - 結果は (date, code) をキーとする辞書リストで返却
    - zscore_normalize は kabusys.data.stats から利用する想定（Research __init__ にて再エクスポート）

Performance / Reliability
- バルク処理とチャンク分割により DB 挿入のオーバーヘッドを削減。
- API リクエストは固定間隔スロットリングでレート制限を順守し、ネットワーク障害や一時的なサーバエラーに対するリトライを実装。
- ニュース収集は各ソース単位で独立してエラーハンドリングするため、1 ソースの失敗が他に波及しない。

Security
- defusedxml を使用した XML パース。
- RSS フェッチにおける SSRF 対策（リダイレクト検査・ホストのプライベートアドレス検出）。
- .env 読み込み時に OS 環境変数を保護する protected 機能。

Notable implementation details / constraints
- duckdb をデータ操作の中心に使用（関数は duckdb.DuckDBPyConnection を前提）。
- 外部ライブラリの使用は最小限（例: defusedxml, duckdb）。Research 内のいくつかのユーティリティは標準ライブラリのみで実装。
- 日次・営業日扱い: 一部のホライズン計算は「営業日ベース（連続レコード数）」を前提とし、スキャン範囲はカレンダー日でバッファを確保している。
- save_* 系関数は PK 欠損行をスキップする挙動（警告ログ出力）。

Known limitations / Future work
- Strategy / Execution / Monitoring の本体実装は初期構成のみ（パッケージ空の __init__.py が存在）。
- 一部のファクター（例: PBR、配当利回り）は未実装（注記あり）。
- データ取得・保存のトランザクション戦略やインデックス最適化等は今後の改善余地あり。

問い合わせ / 貢献
- バグ報告や要望は issue を立ててください。貢献は歓迎します。

---- End of CHANGELOG ----

