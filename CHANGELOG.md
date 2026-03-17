# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
初期リリース（v0.1.0）に含まれる主要な機能・設計方針・安全対策を日本語でまとめています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」のコア機能／データ基盤を実装。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）とバージョン定義（0.1.0）。
  - モジュール公開 API の雛形（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読込（プロジェクトルートの検出: .git / pyproject.toml）。
  - .env/.env.local の優先順位（OS 環境変数 > .env.local > .env）、自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - export 形式、クォート、インラインコメントのパース対応（堅牢な _parse_env_line 実装）。
  - 必須変数チェック（_require）および Settings クラスによるプロパティ化（J-Quants, kabu API, Slack, DB パス, 環境・ログレベル判定等）。
  - 値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と簡易ユーティリティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）を実装：
    - 固定間隔スロットリングによるレート制限遵守（120 req/min をデフォルト）。
    - 再試行（最大 3 回）、指数バックオフ、429 の Retry-After 考慮、408/429/5xx をリトライ対象。
    - 401 受信時はトークンを自動リフレッシュして一度だけリトライ（再帰防止フラグ）。
    - JSON デコード失敗時の明確な例外メッセージ。
  - ID トークン取得（get_id_token）とモジュール内キャッシュ（ページネーション間の共有）。
  - データ取得関数:
    - fetch_daily_quotes（OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
    - 各 fetch 関数は取得ログを出力し、pagination_key を用いた再帰的取得を行う。
  - DuckDB への保存関数（冪等保存を意識した実装）:
    - save_daily_quotes: raw_prices テーブルへの INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへの INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar への INSERT ... ON CONFLICT DO UPDATE
    - 保存時に fetched_at を UTC で記録して Look-ahead Bias のトレースを可能に。
  - データ変換ユーティリティ (_to_float / _to_int) を提供（型変換と不正値処理の方針を明確化）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news に保存する一連の処理を実装。
  - 設計上の特徴:
    - デフォルト RSS ソース（yahoo_finance）を定義。
    - トラッキングパラメータ（utm_ 等）を除去する URL 正規化。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml を用いた XML パース（XML Bomb 等の攻撃防御）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先のスキーム・ホスト検査（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック等であれば拒否（_is_private_host）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検証（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存はトランザクションでまとめて実行、チャンク毎に INSERT ... RETURNING を使い実際に挿入された ID を返す（save_raw_news）。
    - news_symbols（記事と銘柄コードの紐付け）を一括挿入できる内部バルク処理（_save_news_symbols_bulk）と個別 save_news_symbols。
    - 銘柄抽出ロジック（4桁の銘柄コード抽出と既知コードでフィルタリング、重複排除）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）のテーブル定義と初期化関数を追加。
  - 各種テーブル（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義。
  - 主キー、CHECK 制約、外部キー、必要な INDEX を定義してクエリ効率化を考慮。
  - init_schema(db_path) によりディレクトリ作成 → テーブル作成（冪等） → インデックス作成 を行う。get_connection() で既存 DB へ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計と差分更新をサポートする基盤を実装（差分更新・バックフィル・品質チェックの統合を想定）。
  - ETLResult データクラス（結果集約、品質問題・エラーリスト・シリアライズ用 to_dict）。
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - market_calendar を用いた営業日調整ユーティリティ（_adjust_to_trading_day）。
  - 差分更新ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl: 差分取得ロジック（最終取得日 - backfill_days を考慮）、J-Quants から取得して保存するワークフローを実装。取得／保存結果を返却。

### Security
- SSRF 対策（news_collector）:
  - URL スキーム検証、リダイレクト時の事前検証、DNS 解決結果に基づくプライベートアドレス拒否。
- XML 処理に defusedxml を採用して XML 関連の脆弱性（XML Bomb 等）に対処。
- .env 読み込み時に OS 環境変数を上書きしないデフォルト動作と、保護対象キー（protected）を導入。

### Notes / Design decisions
- 冪等性: DB への保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING により冪等化。
- 可観測性: 各処理箇所で logger を利用して取得数・保存数・警告・例外を記録。
- レート制御: J-Quants API の制限を厳格に守るため固定間隔スロットリングを採用（単純かつ確実）。
- テスト容易性: _urlopen 等をモック置換できるよう関数化してある（テストでの置き換えを想定）。

### Deprecated
- （なし）

### Fixed
- （初回リリースのためなし）

---

この CHANGELOG はコードベースから推測して作成しています。将来的なリリースでは各変更ごとに日付・比較対象コミット・影響範囲をより詳細に記載してください。