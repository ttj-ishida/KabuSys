# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

全般的な説明:
- パッケージ名: kabusys
- 初期リリースで、データ取得・保存、ETL パイプライン、ニュース収集、設定管理、DuckDB スキーマなど自動売買システムの基盤機能を提供します。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-03-18

### Added
- 初期リリース: kabusys パッケージ全体の骨組みを追加。
  - src/kabusys/__init__.py にバージョン "0.1.0" と公開モジュール一覧を定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索する実装により、CWD に依存しない読み込みを実現。
  - .env パースの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを正しく処理。
  - .env 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）と検証（KABUSYS_ENV, LOG_LEVEL）を行う。
  - デフォルト DB パス（duckdb, sqlite）や env 判定ユーティリティ（is_live / is_paper / is_dev）を提供。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（_request）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を再試行対象に。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を再取得して 1 回だけ再試行（無限再帰防止機構付き）。
  - ページネーション対応で fetch_daily_quotes / fetch_financial_statements を実装。
  - fetch_market_calendar を実装（祝日・半日・SQ の取得）。
  - データ保存: save_daily_quotes / save_financial_statements / save_market_calendar を実装。DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）し、fetched_at を UTC で記録して Look-ahead バイアスのトレースを可能に。
  - 型安全なユーティリティ: _to_float / _to_int により入力の堅牢な正規化を実現。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news に保存するフローを実装（fetch_rss / save_raw_news / save_news_symbols 等）。
  - セキュリティ強化:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検査、リダイレクト時の検証ハンドラを実装。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後の再チェックによる DoS 対策。
  - URL 正規化と記事 ID の生成:
    - トラッキングパラメータ（utm_* 等）の除去、クエリソート、フラグメント削除を行う _normalize_url。
    - 正規化 URL の SHA-256（先頭32文字）を用いた一意の記事 ID を生成（_make_article_id）し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）および RSS pubDate の堅牢な変換（タイムゾーンを UTC に正規化）。
  - DB 書き込み:
    - バルク INSERT をチャンク化してトランザクションで実行、INSERT ... RETURNING を用いて実際に挿入された記事 ID を返す実装。
    - news_symbols の一括登録関数（_save_news_symbols_bulk）で重複除去およびトランザクション管理を実装。
  - 銘柄抽出: 正規表現に基づく 4 桁コード抽出（extract_stock_codes）と known_codes によるフィルタリングを提供。
  - デフォルト RSS ソースに Yahoo Finance を追加（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Data Platform 構造に基づくスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）を付与してデータ整合性を強化。
  - よく使われるクエリに対するインデックスを作成（idx_*）。
  - init_schema(db_path) により親ディレクトリ自動作成、DDL を冪等に実行し DuckDB 接続を返す API を提供。
  - get_connection(db_path) も提供（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新をベースにした ETL の設計と実装。
  - ETLResult dataclass を追加し、取得数・保存数・品質問題リスト・エラーリストを保持。has_errors / has_quality_errors / to_dict を実装。
  - 差分取得補助: DB の最終取得日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl を実装（差分取得 / backfill_days による後出し修正吸収 / jquants_client による取得と保存）。（※ 初回ロードは _MIN_DATA_DATE をデフォルト開始日として使用）

### Security
- ニュース収集における SSRF 対策、XML パース時の defusedxml 利用、受信サイズ上限、リダイレクト時ホスト検査など多数の防御機構を実装。
- 環境変数の取り扱いで OS 側の既存キーを保護する protected オプションを用意（.env 上書き制御）。

### Performance / Reliability
- API 呼び出しに対するレート制御とリトライ（指数バックオフ）を実装し、外部 API への負荷制御と耐障害性を向上。
- DuckDB へのバルク挿入をチャンク化してトランザクションで処理し、オーバーヘッドを低減。
- raw_* テーブル保存で冪等（ON CONFLICT）を保証し再実行可能な ETL を実現。

### Documentation
- 各モジュールに日本語の docstring と設計方針・処理フローを記載。設定例や使用例も含む。

### Known limitations / Notes
- run_prices_etl 等 ETL 関数は差分取得・backfill の考え方や品質チェックとの連携を実装しているが、品質チェックモジュール（quality）は外部依存として呼び出し側で検討する設計になっています。
- 一部ユーティリティ・関数は将来的に拡張（より詳細なログ、メトリクス収集、テスト用フックの追加など）を想定しています。

## Removed
- （該当なし）

## Fixed
- （該当なし）

## Changed
- （該当なし）

注: 本 CHANGELOG は提供されたコードベースから推測して作成しています。実際の変更履歴や過去リリース情報が存在する場合は、それらに合わせて更新してください。