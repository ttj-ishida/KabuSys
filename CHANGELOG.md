KEEP A CHANGELOGに準拠して、このコードベースから推測される変更履歴を日本語で作成しました。初回リリースとして v0.1.0 を記載し、実装の要点、設計上の注意点、既知の問題点（コード内で見つかった不整合）を明記しています。

CHANGELOG.md
-------------

全般ルール: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（未リリースの変更はここに記載）

[0.1.0] - 2026-03-18
--------------------
Added
- パッケージ初回公開 (kabusys v0.1.0)
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring（空の __init__ ファイルを用意）

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能
    - プロジェクトルートを .git または pyproject.toml から探索して自動読み込み（CWD非依存）
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）
    - .env 読み取り時に既存 OS 環境変数を保護する仕組み（protected）
  - .env パーサーは export 形式、クォート、インラインコメント等に対応
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定をプロパティ経由で取得
    - 値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）および is_live / is_paper / is_dev の判定

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - データ取得:
    - 日足価格 fetch_daily_quotes（ページネーション対応）
    - 財務データ fetch_financial_statements（ページネーション対応）
    - 市場カレンダー fetch_market_calendar
  - HTTP レイヤ:
    - 固定間隔レートリミッタ（120 req/min）を実装（_RateLimiter）
    - 再試行ロジック（指数バックオフ、最大3回）
    - 408/429/5xx をリトライ対象、429 の Retry-After を尊重
    - 401 受信時にリフレッシュを試行して 1 回だけ再試行するトークン自動リフレッシュ
    - id_token のモジュールレベルキャッシュを保持しページネーション間で共有
  - 保存ロジック（DuckDB 連携）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装
    - ON CONFLICT DO UPDATE による冪等性確保
    - fetched_at を UTC で記録して取得時刻をトレース可能に
    - PK 欠損行はスキップしログ出力

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集と DuckDB への保存
  - 主な機能・設計:
    - デフォルト RSS ソースを定義（例: Yahoo Finance）
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字で生成（冪等性）
    - defusedxml を用いた XML パース（XML Bomb 等の対策）
    - SSRF 対策
      - リダイレクト時のスキーム/ホスト検査ハンドラを実装（_SSRFBlockRedirectHandler）
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストならブロック
      - HTTP/HTTPS 以外のスキームを拒否
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の検査（Gzip bomb 対策）
    - テキスト前処理（URL 除去、空白正規化）
    - DuckDB への保存はトランザクションでまとめ、INSERT ... RETURNING により実際に挿入された ID を返す
    - news_symbols による銘柄紐付け（重複除去・チャンク挿入）
    - extract_stock_codes により本文から4桁銘柄コードを抽出（known_codes によるフィルタリング）
  - run_news_collection: 複数ソースを個別に実行し、ソース単位のエラーハンドリングを行う

- DuckDB スキーマ定義 & 初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（CHECK, PRIMARY KEY, FOREIGN KEY）とインデックスを定義してパフォーマンスと整合性を確保
  - init_schema(db_path) でディレクトリ自動作成→テーブル・インデックス作成（冪等）
  - get_connection(db_path) で既存 DB に接続（初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラス（実行結果・品質問題・エラーを含む）
  - 差分更新のヘルパー:
    - 最終取得日を取得する関数群（get_last_price_date / get_last_financial_date / get_last_calendar_date）
    - 非営業日調整 _adjust_to_trading_day（market_calendar に基づく過去方向調整）
  - run_prices_etl の設計:
    - 差分更新（最終取得日 - backfill_days から再取得）に対応
    - デフォルトバックフィル日数 = 3 日
    - fetch → save の流れ（jq.fetch_daily_quotes / jq.save_daily_quotes）
    - id_token を注入可能（テスト容易性）
  - 品質チェック（quality モジュールを想定）を組み込む設計方針（ETL 継続を基本として呼び出し元で対処）

Changed
- 初期リリースのため「変更」はなし

Fixed
- 初期リリースのため「修正」はなし

Security
- ニュース収集での SSRF 対策、defusedxml の採用、レスポンスサイズ制限、許可スキームの明確化などセキュリティ配慮を実施
- .env 読み込みで OS 環境変数を保護する仕組みを追加

Breaking Changes
- なし（初回リリース）

Known issues / Notes
- run_prices_etl の戻り値不整合
  - 関数シグネチャは (int, int) を返すことを期待しているが、ファイルの末尾（現状）では
    return len(records),
    のように末尾にカンマがあり単一要素のタプル (len(records),) を返してしまう可能性がある（保存件数 saved を返していない）。意図した (fetched_count, saved_count) を返すよう修正が必要。
- 設定値未設定時の挙動
  - Settings の必須プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は未設定だと ValueError を送出するため、実運用では .env または環境変数の適切な設定が必要。
- news_collector の DNS 解決失敗時の挙動
  - _is_private_host は DNS 解決に失敗した場合は安全側（非プライベート）として通す実装となっている（誤ブロックを避ける設計）。運用に応じてポリシーを見直すことを検討してください。

開発上の補足（設計思想）
- 冪等性を重視し、外部 API は rate limit と retry を尊重する実装になっています。DuckDB への書き込みは可能な限り ON CONFLICT / RETURNING を用いて正確な変更量を把握できるようにしています。
- セキュリティ面ではネットワークベースの攻撃（SSRF、zip/xml bomb）やリソース消費（大きなレスポンス）への対策を組み込んでいます。
- テスト性を意識し、id_token の注入や _urlopen の差し替え（モック化）が容易な構造にしています。

もし CHANGELOG に含めたい追加の粒度（個々の関数ごとの変更履歴やコミット単位の要約など）があれば、その指示に合わせて更新します。