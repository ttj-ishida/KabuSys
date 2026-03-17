CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
-------------------

初回リリース — KabuSys: 日本株自動売買システムの基礎ライブラリ群を実装。

Added
- パッケージ構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / config
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能（テスト向け）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、引用符（'、"）対応、エスケープシーケンス処理、行末コメント処理などを考慮。
  - 環境変数保護:
    - .env ファイルのロード時に既存の OS 環境変数を保護する protected 機能。
  - Settings クラスを提供（プロパティ経由で設定取得）。
    - J-Quants / kabuステーション / Slack / DB パス / システム設定 (env, log_level, is_live 等) を定義。
    - env と log_level の値検証（許容値チェック）。

- データ取得クライアント / data.jquants_client
  - J-Quants API クライアントを実装。
    - 取得対象: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
  - レート制御:
    - 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行ロジック:
    - 指数バックオフ（最大 3 回）と特定ステータスコード（408, 429, 5xx）に対するリトライ。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証:
    - refresh_token から id_token を取得する get_id_token を実装。
    - 401 受信時は id_token を自動リフレッシュして一度だけリトライする挙動を実装。
    - モジュールレベルの id_token キャッシュ（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements は pagination_key によるページング対応。
    - fetch_market_calendar を実装。
  - DuckDB への保存（冪等性）:
    - save_daily_quotes, save_financial_statements, save_market_calendar において
      INSERT ... ON CONFLICT DO UPDATE により冪等保存を実現。
    - 各保存関数は PK 欠損行のスキップとログ出力を行う。
  - ユーティリティ:
    - 型変換ヘルパー _to_float, _to_int を実装（不正値の安全ハンドリング）。
  - ロギングによる監査情報出力（取得件数・保存件数等）。

- ニュース収集 / data.news_collector
  - RSS フィードからニュース記事を収集し raw_news に保存するモジュールを実装。
  - セキュリティ/堅牢性:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - HTTP/HTTPS スキームの検証（mailto:, file:, javascript: 等を拒否）。
    - SSRF 対策:
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定し拒否。
      - リダイレクト時にも検証するカスタム HTTPRedirectHandler を実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と事前チェック。gzip 解凍後もサイズ検査を実施。
  - URL 正規化・トラッキングパラメータ除去:
    - _normalize_url でスキーム/ホスト小文字化、utm_* 等トラッキングパラメータ削除、フラグメント削除、クエリソートを実施。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭32文字で生成し冪等性を確保。
  - テキスト前処理:
    - URL 除去、空白/改行の正規化を行う preprocess_text を提供。
  - RSS パース:
    - channel/item のフォールバック探索、content:encoded 優先、pubDate のパース（RFC2822 互換）を実装。パース失敗時は現在時刻で代替し警告ログを出力。
  - DB 保存（DuckDB）:
    - save_raw_news: INSERT ... RETURNING を用い、実際に挿入された記事IDを返す。チャンク処理（_INSERT_CHUNK_SIZE）と1トランザクションでのまとめ挿入により効率化。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク挿入で実装。重複除去と INSERT ... RETURNING により正確な挿入数を返す。
  - 銘柄抽出:
    - extract_stock_codes: テキストから 4 桁の銘柄コードを抽出し、既知コードセット（known_codes）と照合して重複排除して返す。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースを順次処理。各ソースは独立してエラー処理し、1 ソース失敗しても残りは継続。新規挿入記事について銘柄紐付けを一括処理。

- DuckDB スキーマ / data.schema
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution）。
  - 主要テーブル（例: raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）を DDL と制約付きで定義。
  - 外部キー・チェック制約・PRIMARY KEY を適切に設定。
  - 頻出クエリ向けのインデックスを複数定義。
  - init_schema(db_path) でディレクトリ自動作成・DDL 実行・インデックス作成を行い、初期化済みの DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン / data.pipeline
  - ETL の設計原則に基づくヘルパー群を実装。
    - 差分更新を行うための最終取得日取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 市場カレンダーヘルパー: _adjust_to_trading_day（非営業日の調整）。
    - ETLResult dataclass を導入し、ETL 実行結果・品質問題・エラーの集約と to_dict を提供。
  - run_prices_etl のベース実装:
    - 最終取得日からの差分再取得（デフォルト backfill_days=3 により後出し修正を吸収）。
    - J-Quants から差分取得し、jq.save_daily_quotes で保存する流れを実装。

Changed
- なし（初回リリースのため着手点のみ）。

Fixed
- なし（初回リリース）。

Security
- ニュース収集での SSRF 対策・XML 安全パーサ利用・レスポンスサイズ上限・スキーム検証など多数の安全対策を組み込み。

Notes / Known issues
- run_prices_etl の戻り値に関して実装上の不備が見つかりました:
  - 現在の実装末尾が "return len(records)," のように見え、(fetched, saved) のタプルを返すことを意図しているが saved 値が返されない可能性があります。追加のコードレビューおよびユニットテストによる修正が必要です。
- その他の機能（strategy、execution、monitoring）モジュールはインターフェース用にパッケージ下に存在するが、実装は今回のリリースでは最小限または空の初期化に留まっています。

今後の改善予定
- run_prices_etl を含む ETL 関数群の完全実装と単体テストの充実。
- quality モジュールによるデータ品質チェックの実装と品質レポーティングの連携。
- strategy / execution の骨子実装（シグナル生成→注文発行→約定/ポジション管理）。
- CI パイプライン、型チェック、より詳細なドキュメントの整備。

----------------------------------------
保持方針・バージョニング: SemVer 準拠を想定。次のリリースでは機能追加は 0.2.0、後方互換性の破壊を伴う変更は 1.0.0 での記録を想定しています。