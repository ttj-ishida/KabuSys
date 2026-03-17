# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-17

リリース: 初回公開

### Added
- パッケージ基盤
  - パッケージ初期化を追加（kabusys/__init__.py）。公開モジュールは data, strategy, execution, monitoring を想定。
  - バージョン番号を 0.1.0 として設定。

- 環境設定/ローディング（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルートの自動検出機能を追加（.git または pyproject.toml を起点）。
  - 自動環境変数ロードの挙動:
    - OS 環境変数 > .env.local > .env の優先順位で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env 読み込みは既存の OS 環境変数を保護する仕組み（protected set）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントなどに対応。
  - Settings に J-Quants / kabu / Slack / DB パス等のプロパティを定義。KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
  - ヘルパー _require により必須環境変数未設定時に明示的な例外を送出。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを取得するクライアントを実装。
  - レート制限管理: 固定間隔スロットリング（120 req/min）を実装する RateLimiter を導入。
  - 再試行・リトライロジック: 指数バックオフによるリトライ（最大 3 回）、HTTP 408/429 および 5xx を対象。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）を実装。
  - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）はページネーション対応。
  - DuckDB への永続化用 save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。いずれも冪等性を確保（ON CONFLICT DO UPDATE）。
  - 保存時に fetched_at を UTC で記録し、「データをいつ知り得たか」をトレース可能に。
  - 安全な型変換ユーティリティ (_to_float, _to_int) を提供（空値・不正値を None に変換、"1.0" のような文字列を適切に扱う）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集し raw_news テーブルに保存するモジュールを実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策: リダイレクト時にスキーム・ホストを検証する _SSRFBlockRedirectHandler、fetch 前のホスト検証、プライベート IP 判定（_is_private_host）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、読み込みで超過した場合は安全にスキップ。gzip 圧縮レスポンスの解凍後にもサイズチェック。
    - 許可スキームは http/https のみ。
  - URL 正規化機能:
    - トラッキングパラメータ（utm_* 等）除去、クエリ整列、フラグメント削除で正規化（_normalize_url）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字で生成（_make_article_id）し、冪等性を保証。
  - テキスト前処理（URL 除去・空白正規化）を実装（preprocess_text）。
  - RSS 解析（fetch_rss）は content:encoded / description / title / pubDate を扱い、pubDate のパース結果を UTC naive datetime に正規化。
  - DB 保存:
    - save_raw_news: チャンク分割（_INSERT_CHUNK_SIZE）＋1トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規追加分の ID リストを返す。
    - save_news_symbols: 記事と銘柄コードの紐付けを INSERT ... RETURNING で保存し、挿入件数を返す。
    - _save_news_symbols_bulk: 複数記事分の銘柄紐付けを重複除去して一括保存する内部関数。
  - 銘柄コード抽出ロジック（extract_stock_codes）を実装。4桁数字候補を known_codes でフィルタして重複を除去。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の4層に基づくテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに適切な型制約・CHECK・PRIMARY KEY および外部キーを定義。
  - 頻出クエリ向けのインデックスを追加（idx_prices_daily_code_date 等）。
  - init_schema(db_path) を実装: 親ディレクトリの自動作成を行い、全 DDL とインデックスを実行して DuckDB 接続を返す（冪等）。
  - get_connection(db_path) を実装: 既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 流れの基礎実装:
    - 差分更新を行うためのヘルパー関数（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーに基づいて非営業日を最近の営業日に調整する _adjust_to_trading_day。
  - ETLResult データクラスを導入（target_date, fetched/saved カウント、quality_issues, errors を含む）。has_errors / has_quality_errors / to_dict を提供。
  - run_prices_etl を実装（差分取得、backfill_days の扱い、_MIN_DATA_DATE のフォールバック、jq.fetch_daily_quotes / jq.save_daily_quotes の利用）。backfill により後出し修正を吸収する設計。

### Security
- ニュース収集で SSRF 対策（ホストのプライベートアドレス判定とリダイレクト時検証）、defusedxml による XML パース実装、HTTP レスポンスサイズ制限など多数の攻撃面に対する防御を導入。
- .env の読み込み時に OS 環境変数を保護（protected set）し、意図しない上書きを防止。

### Notes / Limitations
- strategy および execution パッケージは __init__ のプレースホルダが存在するが、詳細実装は本リリースでは限定的（モジュール構成の骨組みを提供）。
- pipeline.run_prices_etl は株価 ETL の主要ロジックを実装済みだが、品質チェック（quality モジュール）との連携や他 ETL ジョブ（財務・カレンダー等）の統合は今後の拡張対象。
- テストコードはリポジトリ内に含まれていない（ユニットテスト・統合テストは別途追加予定）。

---

今後のリリースでは、strategy の実装、execution（kabu ステーション連携）や監視（monitoring）機能、品質チェックモジュールの実装、テストカバレッジ追加を予定しています。