# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って管理しています。

## [0.1.0] - 2026-03-17

初回リリース (ベース実装)。日本株の自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報: kabusys v0.1.0（src/kabusys/__init__.py に __version__ を追加）
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ で定義

- 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）
  - .env のパース実装（export 形式、クォートとエスケープ、インラインコメントの取り扱い等に対応）
  - 読み込み優先度: OS環境 > .env.local > .env、自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加
  - Settings クラス: J-Quants / kabu API / Slack / データベースパス（DuckDB/SQLite）/ 環境（development/paper_trading/live）/ログレベル検証などのプロパティを提供
  - 必須環境変数未設定時に明確なエラーを投げる _require 実装

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - ベースURL として https://api.jquants.com/v1 を利用
  - レート制限制御: 固定間隔スロットリングで 120 req/min を保証する RateLimiter 実装
  - 冪等かつ堅牢な HTTP リクエスト: 最大リトライ回数、指数バックオフ、408/429/5xx に対するリトライ
  - 401 発生時はリフレッシュトークンから id_token を自動取得して 1 回リトライする機構
  - ページネーション対応での fetch_* 関数:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (四半期 BS/PL)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への保存関数（冪等設計: ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at を UTC ISO8601 で記録
  - 型変換ユーティリティ: _to_float / _to_int（不正値や空値に対応）

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集パイプライン（デフォルトで Yahoo Finance のビジネスカテゴリを参照）
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等の対策）
    - SSRF 対策: リダイレクト先のスキーム検査、ホストのプライベートアドレス判定（DNS 解決した A/AAAA を検査）
    - URL スキームの厳格検証（http/https のみ許可）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止
    - gzip 圧縮解凍後もサイズ検査（Gzip bomb 対策）
  - URL 正規化: トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリソート
  - 記事ID 生成: 正規化 URL の SHA-256 ハッシュ先頭32文字で冪等性を担保
  - テキスト前処理: URL 除去、空白正規化
  - 銘柄コード抽出: 4桁数字を候補とし、既知銘柄セットでフィルタ（extract_stock_codes）
  - DB 保存:
    - save_raw_news: チャンク・トランザクション化した INSERT ... ON CONFLICT DO NOTHING RETURNING を使用して新規挿入 ID を返却
    - save_news_symbols / _save_news_symbols_bulk: (news_id, code) の一括保存（重複除去・トランザクション）

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用 DDL を整備（Raw / Processed / Feature / Execution の層設計）
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - 頻出クエリに備えたインデックス定義
  - init_schema(db_path) により自動ディレクトリ作成とテーブル/インデックス作成を行う（冪等）
  - get_connection(db_path) を提供

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 実行結果を構造的に表現（品質問題・エラーの集約）
  - 差分取得ヘルパー: テーブルの最終取得日取得、取引日調整（_adjust_to_trading_day）
  - run_prices_etl: 差分更新ロジック（最終取得日 - backfill_days からの再取得）、J-Quants からの取得と保存のフローを実装
  - 設計方針として「差分更新を基本、backfill により後出し修正を吸収」「品質チェックは致命的であっても全件継続して収集」等を採用

- その他
  - モジュール構成ファイルの雛形: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を配置（今後の拡張ポイント）

### セキュリティ (Security)
- RSS 周りでの SSRF 対策、defusedxml の採用、レスポンスサイズ制限、gzip 解凍後検査などを実装
- 外部 API 呼び出しにおけるリトライ/バックオフや 401 時のトークン自動リフレッシュで安定性を確保

### 内部設計・運用上の注目点 (Internal / Notes)
- API レート制御はモジュール内の固定スロットリングで実現（120 req/min）
- id_token はモジュールレベルでキャッシュされページネーション間で共有（_ID_TOKEN_CACHE）
- DuckDB に対する INSERT は可能な限り冪等に（ON CONFLICT）しており、raw レイヤは後続処理で信頼して利用可能
- news_collector は記事の重複挿入を SHA-256 ベースの id で回避し、挿入された新規記事のみを元に銘柄紐付け処理を行う

### 既知の問題（Known issues / Caveats）
- run_prices_etl の return 文が実装途中に見える箇所があり（ファイル末尾の "return len(records), "）、呼び出し側が期待する (fetched_count, saved_count) のタプルを正しく返していない可能性があります。リターン値の完成（saved の返却）と単体テストの追加を推奨します。
- strategy/execution/monitoring モジュールは現状でのエントリポイントや実装が最小限（__init__.py のプレースホルダ）にとどまっており、実際の売買ロジック・発注実装はこれからの実装が必要です。
- 一部のエラー処理やログメッセージは基本実装に留まっており、運用時の詳細監視・アラート連携（例: Slack 通知）は実装の余地あり。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

---

注: 本 CHANGELOG はソースコードを基に推測して作成しています。実際のリリースノート作成時はコミット履歴・マージノート・変更要求を参照して適宜修正してください。