# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初期リリース — 日本株自動売買システム "KabuSys" の骨組みと主要コンポーネントを実装しました。

### 追加 (Added)
- パッケージメタ
  - パッケージのバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - 必須環境変数取得ヘルパー (_require) と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）
    - 環境種別（KABUSYS_ENV = development|paper_trading|live）とログレベル検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装：
    - 株価日足（OHLCV）、四半期財務データ、JPX取引カレンダー取得関数（ページネーション対応）
    - 固定間隔スロットリングによるレート制御（120 req/min）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 レスポンスでの ID トークン自動リフレッシュ（1回のみ）
    - モジュールレベルでの ID トークンキャッシュを実装（ページネーション間で共有）
    - JSON デコード失敗時の明示的エラー報告
  - DuckDB への保存関数を実装（冪等性確保）：
    - save_daily_quotes: raw_prices へ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials へ INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar へ INSERT ... ON CONFLICT DO UPDATE
  - 型変換ユーティリティ (_to_float, _to_int) を実装（安全な変換、空値/不正値の扱い）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し DuckDB に保存する一連の機能を実装：
    - fetch_rss: RSS 取得・パース（defusedxml を使用）と記事抽出
    - 前処理: URL 除去、空白正規化（preprocess_text）
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成（_make_article_id）し冪等性を担保
    - SSRF 対策:
      - リダイレクト検査用ハンドラ _SSRFBlockRedirectHandler（スキーム/プライベートIPの検査）
      - ホストがプライベート/ループバック等の場合の事前チェック
    - 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - DB 保存:
      - save_raw_news: チャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id（挿入された新規記事IDを返す）
      - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けを一括挿入（RETURNING で実挿入数を取得）
    - 銘柄コード抽出（四桁数字パターン）と既知銘柄フィルタ（extract_stock_codes）
    - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS を登録

- スキーマ定義 & 初期化 (kabusys.data.schema)
  - DuckDB 向けの完全なスキーマを実装（Raw / Processed / Feature / Execution 層）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切なチェック制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を設定
  - クエリ用インデックスを作成（頻出クエリパターンに対応）
  - init_schema(db_path) でディレクトリ自動作成と DDL 実行（冪等）を提供
  - get_connection(db_path) で既存 DB への接続を提供

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を実装（結果・品質問題・エラー集約）
  - 差分更新ヘルパー:
    - _table_exists, _get_max_date（テーブル最大日付）実装
    - _adjust_to_trading_day（非営業日の調整）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl:
    - 差分更新ロジック（最終取得日 - backfill_days による再取得）
    - J-Quants からの取得と保存（fetch_daily_quotes → save_daily_quotes）
    - backfill_days のデフォルト 3 日、最小取得日は _MIN_DATA_DATE（2017-01-01）
  - ETL の設計方針を踏まえ、品質チェック（quality モジュール）との連携を想定

- その他
  - 空のパッケージモジュールを用意（kabusys.execution.__init__, kabusys.strategy.__init__, kabusys.data.__init__）して今後の拡張ポイントを確保。

### セキュリティ (Security)
- RSS/XML のパースに defusedxml を利用して XML Bomb 等の攻撃に対策。
- RSS フェッチ時に以下の SSRF 防御を実装:
  - URL スキーム検査（http/https のみ許可）
  - ホスト/IP がプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否
  - リダイレクト時に行き先を検査する専用ハンドラを利用
- 受信サイズに上限を設け、gzip 解凍後も検査（メモリ DoS / Gzip bomb 対策）。
- 外部 API 呼び出しでタイムアウトやリトライ対策を導入し、過負荷や不安定なネットワークの影響を軽減。

### 修正 (Fixed)
- 初回リリースのため特段の「修正」はなし（設計・実装の初期投入）。

### 既知の制限 / 注意点 (Known limitations / Notes)
- strategy および execution パッケージは初期状態では実装がない（拡張ポイント）。
- pipeline.run_prices_etl は差分計算・取得・保存の基本を実装していますが、品質チェック（quality モジュール）やエラー集約の詳細ロジックは外部モジュールとの連携を前提としています。
- DuckDB への SQL 実行では文字列連結で DDL/INDEX 文を実行している箇所があり、実行時のパラメタ依存は少ないですが、安全上の注意（外部入力を直接埋め込まない等）を踏まえて運用してください。
- news_collector の DNS 解決失敗時は安全側（非プライベート）とみなす実装のため、特殊なネットワーク環境では挙動の確認が必要です。
- 一部のユーティリティ（例: _to_int の小数扱いなど）は意図的に保守的な変換を行います。運用時にデータ仕様に合わせた調整が必要になる場合があります。

---

開発・運用に関する追加要望や、欠落している機能（戦略実装や発注実行の統合など）があればお知らせください。CHANGELOG は継続的に更新します。