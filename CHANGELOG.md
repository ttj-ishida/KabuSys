# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従って記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-17

初期リリース

### 追加
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring をエクスポート（src/kabusys/__init__.py）。
  - バージョン番号を 0.1.0 に設定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml で判定）。
  - 自動ロード無効化フラグとして KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメントを考慮して安全にパース。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require() を提供。
  - 許容される環境モード（development / paper_trading / live）とログレベル検証を実装。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / Slack / DB パス 等）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する API クライアントを実装。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータス（408, 429, 5xx）で再試行。
  - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして 1 回だけリトライする仕組みを実装。トークンはモジュールレベルでキャッシュ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）を実装。
  - データ保存時に取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスを防止する設計。
  - DuckDB への保存関数は冪等性を持たせる（INSERT ... ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、異常値・空値を適切にハンドリング。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃（XML Bomb 等）を緩和。
    - リダイレクト時にスキームとホスト（プライベート/ループバック等）を検証して SSRF を防止するカスタム HTTPRedirectHandler を実装。
    - HTTP レスポンスの読み込みバイト数上限（MAX_RESPONSE_BYTES = 10MB）を設け、Gzip 解凍後もサイズを検査（Gzip bomb 対策）。
    - URL のスキーム検証（http/https のみ）とホストのプライベート判定を導入。
  - 記事IDの生成: URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート等） → SHA-256 ハッシュ（先頭32文字）を article id として生成し冪等性を確保。
  - テキスト前処理: URL 除去、空白正規化を行う preprocess_text を実装。
  - RSS パースは標準的な channel/item 構造と名前空間付きフィード双方に対応。コンテンツは content:encoded を優先。
  - DB 保存:
    - save_raw_news: バルク挿入（チャンク化）＋トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDの一覧を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存。INSERT ... RETURNING を使用して挿入件数を正確に取得。
  - 銘柄抽出ロジック:
    - 4桁数字（例: "7203"）を候補とする正規表現ベースの抽出（extract_stock_codes）。候補は known_codes セットでフィルタリングし重複除去。
  - 統合ジョブ run_news_collection を実装。各ソースごとに失敗を隔離し、既知銘柄の紐付け処理も実行。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - データプラットフォーム設計に基づく 3 層（Raw / Processed / Feature）と Execution 層のテーブル定義を実装。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を追加。
  - 検索を高速化するためのインデックスを複数定義（銘柄×日付やステータス等）。
  - init_schema(db_path) による初期化関数を提供。既存テーブルはスキップする（冪等）。親ディレクトリが無ければ自動作成。
  - get_connection(db_path) で既存 DB への接続を返すヘルパーを提供。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETL 結果を表す ETLResult dataclass を実装（取得数 / 保存数 / 品質問題 / エラー等を保持）。
  - 差分更新ヘルパー:
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
    - 最終取得日の調整を行う _adjust_to_trading_day（market_calendar を用いた過去方向調整）。
    - raw_prices / raw_financials / market_calendar の最終取得日取得関数（get_last_price_date 等）。
  - run_prices_etl を実装（差分取得、backfill_days による後出し修正吸収、J-Quants クライアント経由の取得と保存）。デフォルトでバックフィル 3 日、最小データ開始日を設定。

### 変更
- 設計上の明示
  - 各モジュールに設計方針やセキュリティ考慮点（Look-ahead 防止、冪等性、SSRF 対策、サイズ制限 等）をドキュメントコメントとして追加。

### セキュリティ
- RSS パースに defusedxml を使用。
- RSS フィード取得時に SSRF 対策（リダイレクト検査、プライベートホスト拒否）を導入。
- HTTP レスポンスサイズ・Gzip 解凍後サイズを検査してメモリ DoS を軽減。

### 既知の制限 / 注意事項
- strategy, execution, monitoring パッケージはエントリポイントとして用意されているが、実装の詳細は今後追加予定。
- ETL パイプラインの品質チェック（quality モジュール）は参照されているが、本リリースでは quality モジュールの内容に依存する箇所がある（quality.QualityIssue 型を利用）。
- run_prices_etl 等の戻り値や細かい例外ハンドリングは今後の実装で拡張される予定。

----

開発・利用に関する問い合わせや改善提案は issue を立ててください。