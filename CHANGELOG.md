Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードの実装内容から推測した変更点・機能説明を記載しています。

CHANGELOG.md
=============
全般
-----
- ドキュメント規約: このファイルは "Keep a Changelog" のフォーマットに従います。
- バージョン番号はパッケージの __version__= "0.1.0" に合わせています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-17
--------------------
初回リリース — 基本的なデータ取得・保存・ETL・ニュース収集基盤を実装。

Added
-----
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring を想定。
  - バージョン情報を 0.1.0 として定義。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を基準に検出することで CWD に依存しない動作を実現。
  - .env パースロジックを実装（コメント、export プレフィックス、クォート、エスケープ、行内コメントの扱いなどに対応）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD オプションを追加。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベルなどの取得と検証を提供（必須値未設定時は ValueError を送出）。
  - env(log) 値のバリデーション（許可値集合）を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得する API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大3回）を実装。408/429/5xx をリトライ対象に設定。429 時は Retry-After を尊重。
  - 401 受信時にリフレッシュトークンから id_token を自動取得して一度だけリトライする仕組みを実装。
  - ページネーション対応（pagination_key）をサポートする fetch_* 関数を実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を担保。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し不正データを安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して DuckDB の raw_news に保存する機能を実装。
  - 既定の RSS ソース（例: Yahoo Finance のビジネスカテゴリ）を定義。
  - XML パースに defusedxml を使用して XML Bomb 等の攻撃を防御。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先スキーム／ホスト検証（内部アドレス・プライベートIPへの到達を拒否）
    - DNS 解決に基づく内部アドレス判定ロジックを実装
  - レスポンスの最大受信バイト数制限（10MB）を導入しメモリ DoS を緩和。gzip 圧縮レスポンスの安全な解凍と解凍後サイズチェックを実装。
  - URL 正規化（クエリパラメータのソート、トラッキングパラメータ除去、フラグメント除去、小文字化）と、それに基づく記事ID生成（SHA-256 先頭32文字）により冪等性を確保。
  - テキスト前処理ユーティリティ（URL 除去、空白正規化）を実装。
  - DB 保存はチャンク化して一 транザクションで行い、INSERT ... RETURNING を用いて実際に新規挿入された記事 ID リストを取得する実装（save_raw_news）。
  - 複数記事の銘柄紐付けを一括挿入する内部関数 _save_news_symbols_bulk を実装。news_symbols への登録は ON CONFLICT DO NOTHING で冪等性を担保。
  - 記事本文・タイトルから 4 桁銘柄コードを抽出する extract_stock_codes を提供（既知コードセットでフィルタ）。

- DuckDB スキーマ/初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - テーブルの CHECK 制約、PRIMARY KEY、外部キー制約を定義。
  - 頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) により親ディレクトリ自動作成後に DDL を順序通り実行してスキーマを初期化するユーティリティを提供。get_connection() も提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を実装して ETL のメタ情報（取得件数、保存件数、品質問題リスト、エラーリスト）を格納。品質問題は辞書化対応。
  - テーブル存在確認、最大日付取得ユーティリティを実装（_table_exists, _get_max_date）。
  - 市場カレンダーを参照して非営業日を直近の営業日に補正する _adjust_to_trading_day を実装。
  - raw_prices/raw_financials/market_calendar の最終取得日を取得するヘルパーを実装（get_last_price_date 等）。
  - 差分更新の方針を実装した run_prices_etl を実装（差分計算、バックフィル日数を考慮した date_from 自動算出、jquants_client を使った取得と保存）。初回ロード用の最小データ日付も定義。

Changed
-------
- n/a（初回リリースのため既存機能の変更はなし）

Fixed
-----
- n/a（初回リリース）

Security
--------
- RSS パースに defusedxml を採用して XML による攻撃を防止。
- RSS フェッチで SSRF 対策を実装（スキーム検証・リダイレクト先検証・プライベートIP拒否）。
- 外部 API 呼び出しでレート制限・リトライ・トークン自動更新を実装し、DoS や認証切れに対して堅牢化。
- .env 読み込みは既存の OS 環境変数を保護するため protected セットを考慮。

Performance & Reliability
-------------------------
- DuckDB への書き込みでは ON CONFLICT とチャンク挿入、トランザクションまとめにより冪等性とパフォーマンスを確保。
- API 呼び出しは固定間隔スロットリングと指数バックオフでレート制限とリトライの両立を図る。
- RSS 受信は Content-Length と実際読込バイト数の両方でサイズチェックを行い、gzip 解凍後もサイズ検証を実施。

Notes / Known limitations
-------------------------
- strategy と execution パッケージはプレースホルダ（__init__.py のみ）であり、戦略実装や発注ロジックはこれから実装予定。
- ETL パイプラインは prices の差分 ETL を実装済み。financials / calendar の ETL 統合や品質チェックモジュール（quality）の詳細実装は別途実装が必要（pipeline が quality モジュールを参照している設計になっている）。
- J-Quants からのデータ保存は DuckDB のスキーマ定義に依存するため、既存スキーマを変更する場合はマイグレーションが必要。
- 単体テスト・統合テストについてはテストフックが一部（_urlopen モック可能、id_token 注入可能）備わっているが、網羅的なテスト実装は今後の課題。

Authors
-------
- 実装元コードを元に CHANGELOG を作成（コード内の設計コメントを反映）。

ライセンス
---------
- （コードベースのライセンス表記がないためここでは省略。実運用時は LICENSE を追加してください。）

-- 以上 --