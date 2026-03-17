# Change Log

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

※この CHANGELOG は提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

- 今後のリリースでの改善候補（推測）
  - ETL の完成（prices ETL の戻り値の整合性・他ジョブの実装）
  - strategy / execution / monitoring モジュールの具現化（現在はパッケージプレースホルダ）
  - 単体テスト・統合テストの追加（ネットワーク関連のモック含む）
  - ドキュメント（API 使用例、データスキーマ仕様書）の拡充

---

## [0.1.0] - 2026-03-17

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - サブパッケージ（プレースホルダ）: data, strategy, execution, monitoring

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの読み込みを実装
  - 自動ロードの優先度: OS 環境変数 > .env.local > .env
  - 自動ロード抑止フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を導入（テスト等で利用可能）
  - .env パーサ:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォート有無を考慮）
    - ファイル読み込み失敗時に警告発行
    - protected 引数で OS 環境変数上書きを防止
  - Settings クラスを公開 (settings):
    - J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル判定プロパティ
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値検査）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - token 取得 (get_id_token)
    - 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）の取得（ページネーション対応）
  - レート制御:
    - 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）
  - 再試行/リトライ:
    - 指数バックオフ、最大 3 回リトライ（408/429/5xx を対象）
    - 429 の場合は Retry-After を優先
  - トークン自動リフレッシュ:
    - 401 受信時に ID トークンを 1 回自動リフレッシュしてリトライ
    - get_id_token 呼び出しからの無限再帰対策
  - 冪等性:
    - DuckDB への保存は ON CONFLICT DO UPDATE を利用して重複排除・更新（save_daily_quotes / save_financial_statements / save_market_calendar）
  - データ整形ユーティリティ:
    - 値変換ヘルパー _to_float / _to_int（安全な変換ロジック）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集と raw_news への保存機能を実装
  - セキュリティ・堅牢性対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先検査用ハンドラ _SSRFBlockRedirectHandler、ホストがプライベート IP の検出（_is_private_host）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と超過検出（読み取り上限／gzip 解凍後チェック）
    - gzip 解凍エラーのハンドリング（gzip bomb の検出）
  - データ正規化:
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字（冪等性の確保）
    - テキスト前処理（URL 除去、空白正規化）
    - pubDate のパース（タイムゾーンを UTC に正規化、パース失敗時は代替時刻を使用）
  - DB 保存機能:
    - save_raw_news: チャンク分割（_INSERT_CHUNK_SIZE）＋トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された ID のみ返す
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（重複排除、トランザクション）
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を検出し、known_codes に存在する物のみ返却（重複除去）

- DuckDB スキーマと初期化（kabusys.data.schema）
  - 3 層構造（Raw / Processed / Feature）および Execution 層のテーブル DDL を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成と DDL 実行（冪等）
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult データクラス（結果集約、品質問題・エラーの収集、シリアライズ用 to_dict）
  - 差分更新ロジック補助:
    - DB の最終取得日取得ヘルパ（_get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）
    - 非営業日調整ロジック（_adjust_to_trading_day）
  - run_prices_etl 実装開始:
    - 差分更新（last date を元に date_from を自動算出、デフォルト backfill_days=3）
    - 指定範囲のデータ取得 → save_daily_quotes により保存（冪等）
    - ロギングと (fetched, saved) の返却を意図（ただしソース断片のため戻り値の完全性は今後整備予定）
  - 設計方針:
    - ETL は後出し修正を吸収するためのバックフィルを行う
    - 品質チェック（quality モジュール）と分離して動作、重大エラーでも収集処理を継続する設計（Fail-Fast ではない）
    - id_token を注入可能にしてテスト容易性を向上

Changed
- 初期バージョン（0.1.0）としてプロジェクトのコア機能を整備。以降は各サブモジュールの実装拡張・安定化を予定。

Security
- RSS/XMl に対するセキュリティ対策を強化（defusedxml、SSRF/プライベートIP検査、レスポンスサイズ制限、gzip 解凍後チェック）
- .env 読み込み時に OS 環境変数の上書きを保護する仕組みを導入

Notes / Known limitations
- strategy、execution、monitoring パッケージは現時点ではプレースホルダ（実装は今後）
- pipeline モジュールの一部関数（例: run_prices_etl の戻り値ハンドリングなど）は拡張の余地あり（コード断片のため一部未完成の可能性）
- 外部ネットワーク呼び出し部分はテスト時にモック可能な設計だが、実稼働前に統合テストの整備が必要
- DuckDB を前提としているため、実運用時のバックアップ・マイグレーション戦略は別途検討が必要

---

今後のリリースでは下記の改善を想定しています（例）:
- 全 ETL ジョブの完成と品質チェック（quality モジュール）との統合
- strategy / execution の実装（シグナル生成、発注・注文管理）
- 単体テスト・CI の整備、テストカバレッジ向上
- 運用向けログ・監視の追加（Slack 通知など）

（以上）