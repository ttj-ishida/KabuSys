CHANGELOG
=========

すべての重要な変更は、Keep a Changelog の形式に従って記載しています。  
このファイルは人間が読めるように変更履歴をまとめたものであり、バージョン管理の参照用に利用してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- なし

[0.1.0] - 2026-03-18
--------------------
初回リリース (ベース実装)。主に日本株自動売買システムのコアライブラリ群とデータ基盤周りの実装を追加しました。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - __all__ に data, strategy, execution, monitoring を公開（サブモジュール構成の意図を明示）。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを自動実行（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env/.env.local の読み込み順序をサポート（OS 環境変数 > .env.local > .env）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの実装: export 形式、クォート処理、インラインコメントの取り扱いを考慮した堅牢なパース処理。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス等のプロパティを公開。環境値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値等）を実装。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を尊守する RateLimiter を導入。
  - リトライロジック: 指数バックオフを用いた最大 3 回の再試行、HTTP 429/408/5xx の再試行対応。
  - 401 レスポンス時の自動トークンリフレッシュ（1 回だけ）と再試行機構。
  - ページネーション対応（pagination_key 共有、重複ループ防止のためのキャッシュ）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - fetched_at を UTC 形式で記録し、Look-ahead バイアスのトレーサビリティを確保。
    - ON CONFLICT DO UPDATE により冪等保存を実現。
    - 型安全な変換ユーティリティ（_to_float, _to_int）を実装。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集 (fetch_rss)、前処理 (preprocess_text)、記事ID生成（正規化 URL の SHA-256 の先頭 32 文字）を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の緩和）。
    - SSRF 対策: リダイレクト検査ハンドラ、ホストがプライベート/ループバック/リンクローカルかの判定、http/https スキームのみ許可。
    - レスポンス長上限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後のサイズチェック。
    - トラッキングパラメータ除去（utm_*, fbclid 等）による URL 正規化。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事 ID を返す実装。
    - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けをトランザクションで一括挿入し、実際に挿入された件数を返す実装。
  - 銘柄コード抽出 (extract_stock_codes): 4 桁数字候補から known_codes に含まれるコードのみ抽出する実装。
  - 統合収集ジョブ (run_news_collection): 複数ソースの独立ハンドリング、記事保存 → 新規記事のみ銘柄紐付けを行うフローを実装。
  - デフォルト RSS ソースを提供（例: Yahoo Finance のビジネスカテゴリ）。
- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform 指針に基づくスキーマ定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - インデックス定義とテーブル作成順を用意。
  - init_schema(db_path) によりディレクトリ作成を含めた初期化処理を提供。get_connection(db_path) も実装。
- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラス（品質チェック結果とエラー集約、辞書化用メソッドを含む）を追加。
  - 差分更新ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day（非営業日の調整）
    - _table_exists / _get_max_date
  - run_prices_etl: 差分更新のロジック（最後の取得日から backfill するデフォルト動作）を実装。J-Quants から取得して保存する流れを構築。
  - ETL の設計方針（差分更新、backfill_days、品質チェックは Fail-Fast ではない等）をコード内に明確化。
- その他
  - ロギングを各モジュールで適切に出力（info/warning/exception）。

Security
- defusedxml を利用して RSS/XML パースに対する攻撃緩和。
- news_collector における SSRF 対策（リダイレクト検査、プライベートアドレスブロック、スキーム検証）。
- .env 読み込み時のファイル読み取り失敗を warnings.warn で扱い、実行停止を避ける設計。

Changed
- なし（初版のため変更履歴はなし）。

Fixed
- なし（初版）。

Removed
- なし（初版）。

Known issues / Notes
- pipeline.run_prices_etl の戻り値注釈は (int, int) を想定していますが、実装の末尾が "return len(records)," のように片方のみ返している形になっており、呼び出し側で期待される戻り値数と不整合が発生する可能性があります（意図しないタプル構造となる・型不整合）。リリース後早期に修正を推奨します。
- strategy、execution、monitoring パッケージの __init__ は空で、各サブパッケージの実装はこれから追加される想定です。
- テスト補助: news_collector._urlopen をモックして HTTP 周りのテストを行う想定。実運用環境での追加テスト・堅牢化が必要です。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN 等の環境変数が必須。`.env.example` を参考に設定してください。

Contributors
- 初期実装: コードベースから推測してドメイン設計者による実装。

今後の予定
- run_prices_etl の戻り値整合性修正と追加 ETL ジョブ（financials, market_calendar）の完備。
- strategy / execution / monitoring の実装追加。
- 単体テストの整備と CI パイプラインの導入。
- ドキュメント（DataPlatform.md, API 使用例、運用手順）の充実。

-----
注: 本 CHANGELOG は提示されたソースコードからの推測に基づき自動作成しています。実際のコミット履歴やリリースノートに基づく正式なCHANGELOGは、バージョン管理履歴をもとに作成することを推奨します。