# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このプロジェクトはセマンティック バージョニングを使用します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本メタ情報を追加（src/kabusys/__init__.py、バージョン 0.1.0）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env と .env.local を読み込み（OS環境変数を保護）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（コメント、export 形式、クォート・エスケープ対応、インラインコメント処理）。
  - 必須設定取得時に未設定なら例外を出すヘルパー _require。
  - 有効な環境 (development/paper_trading/live) とログレベル検証を実装。
  - 主な設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV, LOG_LEVEL

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
  - API レート制御（固定間隔スロットリング）を実装し、デフォルトで 120 req/min を遵守。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）を実装。
  - 401 発生時はリフレッシュトークンにより id_token を自動更新して 1 回リトライ（無限再帰防止）。
  - id_token キャッシュをモジュールレベルで共有（ページネーション間で使用）。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE による冪等性を確保）。
  - 取得時刻（fetched_at）を UTC 表記で記録して Look-ahead Bias のトレースを可能に。
  - 型変換ユーティリティ _to_float / _to_int を実装（安全な変換と不正値の扱い）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存する機能を実装。
  - 設計上の特徴:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - defusedxml を使用して XML 攻撃（XML bomb 等）を防御。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート IP 判定、リダイレクト時の事前検査ハンドラ実装。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後のサイズ再検査（Gzip bomb 対策）。
    - テキスト前処理（URL 除去・空白正規化）。
    - DB 保存はチャンク化して INSERT ... RETURNING を使い、新規挿入された ID を正確に取得。トランザクションでまとめて処理。
    - 銘柄コード抽出（4 桁数字パターン）と news_symbols テーブルへの紐付けを実装。
  - API:
    - fetch_rss(url, source, timeout) → NewsArticle リスト
    - save_raw_news(conn, articles) → 新規挿入された記事 ID リスト
    - save_news_symbols / _save_news_symbols_bulk による銘柄紐付け
    - run_news_collection: 複数ソースを一括収集し DB へ保存・紐付けを行うジョブ

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の層に基づく包括的なスキーマを実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PK、FOREIGN KEY、CHECK）と検索パフォーマンス向けのインデックスを定義。
  - init_schema(db_path) によりファイル/メモリ DB の初期化とテーブル作成（冪等）を実装。親ディレクトリ自動作成。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL の基本機能を実装（設計の一部が実装済み）。
  - ETLResult データクラス: ETL 実行結果（取得数、保存数、品質問題、エラー等）を格納。
  - 差分取得のためのヘルパー:
    - _table_exists, _get_max_date（任意テーブルの最大日付取得）
    - _adjust_to_trading_day（非営業日の調整）
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl: 株価日足の差分 ETL を実装（date_from 自動算出、backfill による後出し修正吸収、jquants_client の fetch/save を呼び出す）。

### セキュリティ (Security)
- RSS パーサで defusedxml を使用して XML の脆弱性を低減。
- RSS フェッチ時に SSRF 対策を複数実装:
  - URL スキーム制限（http/https のみ）
  - ホストがプライベート/ループバック/リンクローカルでないかを検査
  - リダイレクト先の検査を行うカスタムリダイレクトハンドラ
- 外部 API 呼び出し時にリトライや RateLimiter を設けて過負荷や不正な応答への対策を実施。
- .env 読み込みはプロジェクトルートから行い、OS 環境変数はデフォルトで保護される。

### その他・設計上の注意 (Notes)
- DuckDB スキーマは初期化時に既存テーブルがあれば上書きせずスキップするため、既存データの保持が可能。
- jquants_client の _request は JSON デコード失敗時に詳細な例外を投げるため、上流でのログ確認が有用。
- news_collector の extract_stock_codes は与えられた known_codes のセットに基づいて抽出するため、事前に有効銘柄コードリストを渡すこと。
- 現在の ETL 実装は run_prices_etl の途中まで実装（コードスナップショットの末尾で戻り値のタプルが途中で切れている可能性があるため、実際の呼び出し時は完全実装を確認してください）。

### 既知の問題 (Known issues / TODO)
- pipeline.run_prices_etl の戻り値の記述がコードスニペットの末尾で不完全に見える（実装の続き確認が必要）。
- strategy/execution/monitoring パッケージの中身は現時点では未実装（パッケージエントリのみ存在）。
- 単体テスト、統合テストはコードスナップショットに含まれていないため実運用前に追加を推奨。

---

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際の履歴やリリース日・マイグレーション手順はプロジェクトの正式なリポジトリ履歴に基づいて調整してください。