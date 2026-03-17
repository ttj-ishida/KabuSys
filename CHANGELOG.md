# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

全般方針:
- 安全性（SSRF・XML攻撃・メモリDoS）と冪等性（DB保存の ON CONFLICT / RETURNING）を重視した実装。
- テスト容易性のために外部依存（HTTP 呼び出し・ID トークン）を注入可能に設計。
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュを組み込んだ堅牢なクライアント実装。

## [0.1.0] - 2026-03-17
初回リリース

### Added
- 基本パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開サブパッケージ指定。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込むユーティリティを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を導入し、カレントワーキングディレクトリに依存しない自動読み込みを実現。
    - .env 解析機能を強化（export プレフィックス対応、クォート中のエスケープ、インラインコメントの扱い）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は override）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパー _require() と Settings クラス（J-Quants / kabu API / Slack / DB パス等）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証ロジックを実装。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出し（/prices/daily_quotes, /fins/statements, /markets/trading_calendar）を行う fetch_* 関数を実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回）を導入。対象はタイムアウト/429/408/5xx 等。
    - 401 レスポンス時の ID トークン自動リフレッシュ（1 回のみ）を実装。
    - ページネーション対応（pagination_key による継続取得）。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。いずれも冪等化（ON CONFLICT DO UPDATE）される。
    - データ型変換ユーティリティ _to_float / _to_int を提供（空値や不正値を安全に処理）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を取得して raw_news に保存する機能を実装。
    - 設計上の注意点: defusedxml による XML 攻撃対策、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化ロジック（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字を用いることで冪等性を保証。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合アクセス拒否、リダイレクト時に検査するカスタムハンドラを導入。
    - RSS のパースと article 構築（content:encoded 優先・description フォールバック、pubDate の RFC2822 パースと UTC 正規化）。
    - DB 保存: save_raw_news（INSERT ... RETURNING を使用し、chunk 単位でトランザクション内にて挿入）、save_news_symbols / _save_news_symbols_bulk（銘柄紐付けをバルク挿入、ON CONFLICT で重複を無視）。
    - 銘柄コード抽出ロジック extract_stock_codes（テキスト中の 4 桁数字を候補とし、known_codes にあるもののみ採用）。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を実装（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, など）。
    - 各テーブルの制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
    - 使用頻度の高いクエリに対するインデックスを定義。
    - init_schema(db_path) でディレクトリ作成を含めた初期化処理を行い、冪等にテーブルを作成。
    - get_connection(db_path) を実装。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETL 実行結果を表す ETLResult dataclass（品質問題・エラーの集約・変換メソッド含む）を実装。
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists / _get_max_date）。
    - 市場カレンダーに基づく営業日調整ヘルパー _adjust_to_trading_day。
    - 差分取得用のユーティリティ get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - run_prices_etl 実装（差分計算、backfill_days による後出し修正吸収、fetch -> save の流れ）を追加。
    - 設計上、品質チェックモジュール（quality）と連携して問題を収集する方針を反映。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- XML パーサに defusedxml を採用し、XML ブロブ攻撃を軽減。
- RSS フィード取得での SSRF 対策を導入（スキーム検証、プライベート IP の拒否、リダイレクト検査）。
- HTTP レスポンスの読み込み上限（MAX_RESPONSE_BYTES）・gzip 解凍後サイズチェックを追加してメモリ DoS を防止。

### Notes / Known issues
- run_prices_etl の実装末尾に戻り値が不完全な箇所が見つかります（現状ソースの最後が `return len(records), ` のように2要素タプルを期待する箇所で1要素しか返していない）。呼び出し側で (fetched, saved) の2要素を期待しているため、呼び出し時に例外や値の不整合が発生する可能性があります。次版で修正予定。
- このリリースでは strategy / execution パッケージの具体的な戦略ロジックや kabu ステーションとの発注処理の実装は含まれていません（パッケージ骨格は提供済み）。

---

今後の予定（短期）
- run_prices_etl の戻り値不備修正と単体テスト追加。
- quality モジュールによるデータ品質チェックの統合と ETL の結果への反映処理強化。
- strategy / execution 層の実装拡充（シグナル生成・発注処理の実装、kabu API クライアントの追加）。
- テストカバレッジ拡充（ネットワーク呼び出しや外部依存のモック化を含む）。

以上。