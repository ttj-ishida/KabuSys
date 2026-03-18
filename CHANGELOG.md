CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-18
--------------------

初回リリース。日本株自動売買プラットフォームのコアコンポーネントを実装しました。
主要な追加点、設計方針、安全対策、DBスキーマなどを下記にまとめます。

Added
- パッケージ初期定義
  - kabusys パッケージを追加。__version__ = "0.1.0"。
  - サブパッケージの公開インターフェースを定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env または環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git / pyproject.toml から検出し、.env → .env.local の順に読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、クォート文字列のエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 環境モード等の設定をプロパティ経由で取得。必要な環境変数が未設定の場合は明示的に ValueError を送出。
  - KABUSYS_ENV、LOG_LEVEL のバリデーション（許可値チェック）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得 API のラッパーを実装。
  - レート制限対応（_RateLimiter による固定間隔スロットリング、120 req/min）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を考慮）。429 の場合は Retry-After ヘッダ優先。
  - 401 のときはリフレッシュトークンで id_token を自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
  - ページネーション対応（pagination_key を追跡）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を確保。
  - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias を防止できる設計。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news に保存するモジュールを実装。
  - 記事ID は URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。utm_* 等のトラッキングパラメータを除去。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - 初回とリダイレクト先のホストをプライベートアドレス判定で拒否（_is_private_host）。
    - リダイレクト時にスキーム/ホストを検査するカスタム HTTPRedirectHandler を実装。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 展開後のサイズ検査を実施（Gzip bomb 対策）。
  - コンテンツ前処理（URL 除去、空白正規化）とタイトル/本文の統合による銘柄コード抽出機能（4桁コード抽出 + known_codes でフィルタ）。
  - DB 保存はトランザクションでまとめ、チャンク（_INSERT_CHUNK_SIZE）分割、INSERT ... RETURNING を使って実際に挿入された件数を正確に返す。
  - デフォルト RSS ソースとして Yahoo Finance カテゴリを追加（DEFAULT_RSS_SOURCES）。

- スキーマ（kabusys.data.schema）
  - DuckDB 用の包括的スキーマを実装（Raw / Processed / Feature / Execution 層を想定）。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw 層テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層を定義。
  - features, ai_scores など Feature 層を定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層を定義。
  - 適切な PRIMARY KEY、CHECK 制約、外部キー、インデックス（頻出クエリ向け）を含む DDL を提供。
  - init_schema(db_path) によりディレクトリ作成→DDL 実行→インデックス作成まで行い、冪等に初期化可能。
  - get_connection(db_path) で既存 DB に接続するユーティリティを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を想定した ETL ヘルパーを実装（最終取得日から backfill を行う戦略）。
  - ETLResult dataclass により ETL の取得数・保存数・品質問題・エラーを集約。
  - テーブル存在チェック、最大日付取得関数、営業日調整ロジック（market_calendar を用いた過去方向調整）を実装。
  - 個別ジョブ run_prices_etl の骨格実装（差分取得→保存→ログ）。（バックフィル日数等はパラメータ化）

Changed
- なし（初回リリースのため新規実装中心）

Fixed
- データ変換ユーティリティを実装し、型変換時の例外や不整合を安全に扱うようにした:
  - _to_float / _to_int: 空値や不正な文字列を None に落とす。float 文字列からの int 変換は小数部が 0 の場合のみ許容。

Security
- API/ネットワーク処理や外部入力に対する多層防御を導入:
  - J-Quants クライアントのタイムアウト、リトライ、レート制限。
  - RSS パーサで defusedxml を使用（XML 脅威対策）。
  - SSRF 防止（スキーム検証、プライベート IP/ホストの排除、リダイレクト時の検査）。
  - 大きなレスポンスの拒否と gzip 展開後のサイズ検査（メモリ DoS / Gzip bomb 対策）。
  - DB周りは可能な限りトランザクションでまとめ、ON CONFLICT を用いることでデータ整合性と冪等性を確保。

Performance
- DB 書き込みをチャンク化して一括 INSERT を行うことでオーバーヘッドを削減（news_collector のチャンク挿入、news_symbols の一括保存、save_* の executemany）。
- レート制御により外部 API の制限を遵守。

Documentation
- モジュール docstring と関数ドキュメントで設計方針、前提条件、エラー動作を明示（例: ETL の差分更新方針、news_collector の設計目的等）。

Known issues / Limitations
- run_prices_etl など ETL ジョブのうち一部は骨格実装（処理フローは実装済みだが、さらなる品質チェック/例外ハンドリングの拡充が可能）。
- NewsCollector のホスト判定は DNS 解決失敗時に「非プライベート」とみなす仕様（安全側での誤検出を抑える意図だが、環境により振る舞いに差が出る可能性あり）。
- J-Quants API のトークンといった機密情報は環境変数経由で管理する設計のため、適切な運用（.env の保護、CI シークレット管理）が必要。

Deprecated
- なし

Security policy
- なし（運用上の注意をドキュメントに含む）

Acknowledgements
- 本リリースはモジュール別にセキュリティ・冪等性・可観測性を重視して設計・実装されました。今後のリリースで監視、実行連携、戦略モジュールの実装・テストを強化していきます。