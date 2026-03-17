# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-17
初期リリース。以下の主要機能・構成を追加しました。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開 API を定義 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルと環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートの自動検出 (.git または pyproject.toml を基準)
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env 解析の堅牢化（export プレフィックス、クォートやエスケープ、コメント処理など）
  - Settings クラスを導入し、アプリケーション設定をプロパティで提供
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等
    - env, log_level のバリデーション（許容値チェック）
    - duckdb/sqlite のデフォルトパスを提供
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX 市場カレンダー取得機能を実装
  - レート制御 (120 req/min) を固定間隔スロットリングで実装（RateLimiter）
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対応）
  - 401 を受信した際の自動トークンリフレッシュ（1回のみ）実装
  - ページネーション対応の fetch 関数（fetch_daily_quotes, fetch_financial_statements）
  - データ取得時の fetched_at（UTC）記録と、DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ (_to_float, _to_int)
- ニュース収集（RSS）モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得 → 前処理 → DuckDB へ冪等保存 のフローを実装
  - 記事ID を URL 正規化（トラッキングパラメータ除去）後の SHA-256（先頭32文字）で生成し冪等性を保証
  - XML パースに defusedxml を使用して XML-based 攻撃を軽減
  - SSRF 対策
    - URL スキーム検証 (http/https のみ許可)
    - リダイレクト時にスキーム／ホストを検証するカスタム RedirectHandler を導入
    - プライベートアドレス判定（IP 直接解析 + DNS で解決した A/AAAA をチェック）
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
  - トラッキングパラメータ除去、URL 正規化、テキスト前処理（URL 除去・空白正規化）
  - DB 保存はトランザクションでまとめ、INSERT ... RETURNING を使って実際に挿入された ID を返す実装
  - 銘柄コード抽出（4桁数値パターン）と news_symbols への一括紐付け機能
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を提供
- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層 + 実行層を想定したテーブル定義を実装
    - raw_prices, raw_financials, raw_news, raw_executions 等
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等
    - features, ai_scores（特徴量/AIスコア用）
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の実行層
  - 各種制約（CHECK, PRIMARY KEY, FOREIGN KEY）を定義
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date 等）
  - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成（冪等）
  - get_connection() を提供
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL の骨組みを実装
    - DB の最終取得日を参照して差分（および backfill）で取得
    - J-Quants クライアント経由で取得・保存（冪等）
    - 品質チェック（quality モジュールとの連携を想定）の枠組み
  - ETL 実行結果を表す ETLResult データクラス（品質問題・エラー情報の集約）
  - 市場カレンダーに基づく営業日調整ヘルパー、テーブル最終日取得ユーティリティを提供
  - run_prices_etl の基礎実装（差分判定 → fetch → save の流れ）
- その他ユーティリティ
  - URL 正規化、トラッキングパラメータ除去等のユーティリティ関数を多数実装
  - RSS パースでの日時取り扱い（RFC 日時の UTC 変換）や入力健全性チェック
  - DB 保存時のチャンク処理（INSERT のバルクサイズ管理）

### Security
- SSRF 対策を導入（news_collector）
  - URL スキーム検証、プライベート/ループバック/リンクローカル判定、リダイレクト先検査
- XML パースで defusedxml を使用し XML-based 攻撃を軽減
- 外部入力（.env）読み込み時の安全策（ファイル読み込み失敗時の警告など）

### Changed
- 初期リリースのため該当なし

### Fixed
- 初期リリースのため該当なし

### Deprecated
- 初期リリースのため該当なし

### Removed
- 初期リリースのため該当なし

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。細かい API 仕様や公表日付はコード内コメント・定義を基に決定しました。今後の変更はこのフォーマットで追記してください。