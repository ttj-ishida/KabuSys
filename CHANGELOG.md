# CHANGELOG

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを採用します。

現在のバージョン: 0.1.0

Unreleased
---------
- 注意事項 / TODO
  - run_prices_etl() の戻り値が現状不完全（len(records), のような途中の形で終わる箇所が存在）ため、ETL 呼び出し側での取り扱いに注意が必要。次リリースで戻り値タプルの最終化（prices_saved を含めた正しい返却）を行う予定。
  - 単体テストや結合テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を利用した設定制御のテストを拡充予定。
  - 監査・品質チェック（quality モジュール）との連携ロギングやエラー分類の強化を予定。

0.1.0 - 2026-03-18
-----------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定／環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env ファイルのパース強化:
    - export KEY=val 形式対応、クォート文字列内のバックスラッシュエスケープ対応、インラインコメント処理、コメントルールの明確化。
  - Settings クラス提供: J-Quants / kabuステーション / Slack / DB パス / ログレベル / 実行環境 (development/paper_trading/live) 等のアクセスプロパティ。
  - 必須環境変数未設定時は ValueError を送出する _require を実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足、財務データ、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - get_id_token() によるリフレッシュトークン→IDトークン取得（POST）。
  - HTTP ユーティリティ:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 指数バックオフを含むリトライロジック（最大 3 回、408/429/5xx を対象）。
    - 401 の場合は自動でトークンリフレッシュして 1 回のみリトライ（無限再帰防止）。
    - JSON デコード失敗時の明確なエラー報告。
  - DuckDB への保存関数（冪等設計）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE により重複を排除し、fetched_at を UTC で記録。
    - PK 欠損行はスキップし、スキップ件数を警告ログ出力。
  - 型変換ユーティリティ _to_float / _to_int を実装（堅牢な変換ルール）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存するフロー実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証・リダイレクト先の事前検証・プライベートアドレス拒否。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保（utm_ 等のトラッキングパラメータを除去）。
  - fetch_rss(): フィード取得、gzip 解凍、XML パース、item 抽出、前処理（URL 除去・空白正規化）、pubDate のパース（UTC 換算）。
  - DB への保存関数:
    - save_raw_news(): チャンク化して INSERT ... RETURNING id を使用し、実際に挿入された記事IDのみを返す（トランザクションでまとめる）。
    - save_news_symbols() および内部の _save_news_symbols_bulk(): news_symbols テーブルへの紐付けをチャンク挿入し、実挿入数を返却。
  - テキストからの銘柄コード抽出関数 extract_stock_codes(): 4桁数字パターンを検出し、既知コードセットでフィルタ（重複除去）。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md に基づくスキーマ定義と init_schema() を実装。
  - 3層（Raw / Processed / Feature / Execution）をカバーするテーブル群を作成:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を定義。
  - 頻出クエリ用のインデックス群を定義し作成。
  - init_schema(db_path) は親ディレクトリ自動作成、DDL の冪等実行を行う。
  - get_connection() を提供（スキーマ初期化は行わない）。

- ETL パイプライン基礎 (src/kabusys/data/pipeline.py)
  - ETL の設計に基づく基本ユーティリティと run_prices_etl 等の骨組みを実装。
  - ETLResult dataclass を導入し、取得件数・保存件数・品質問題・エラーを集約可能に。
  - 最終取得日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場日（営業日）調整ヘルパー _adjust_to_trading_day。
  - run_prices_etl(): 差分更新ロジック（最終取得日に基づく date_from 自動決定、backfill による後出し修正吸収）、fetch → save の呼び出しを実装（現状ファイル末尾に戻り値処理が途中の記述あり、後続修正予定）。

Changed
- （初期リリースのためなし）

Fixed
- （初期リリースのためなし）

Security
- ニュース収集処理における SSRF 対策、defusedxml の導入、最大受信バイト数制限、gzip 解凍後の検査など、外部入力に対する複数の防御を追加。

Documentation
- 各モジュールに詳細な docstring と設計方針、呼び出し方・注意点を明記（コード内コメントベース）。

Notes
- 本リリースは基盤機能の初期実装を中心としており、品質チェック（quality モジュール）との統合点やパイプラインの完全なエンドツーエンド確認、unittests/integration tests の整備は今後の作業対象です。
- run_prices_etl の戻り値に関する未完の箇所があり、ETLResult 等との整合性は次バージョンで修正予定です。

今後の予定
- run_prices_etl の戻り値修正と追加の個別 ETL ジョブ実装（financials, calendar の差分ETL 完全化）。
- quality モジュールとの統合強化（品質問題のログ/通知・閾値設定）。
- strategy / execution / monitoring モジュールの実装拡張と E2E テスト整備。