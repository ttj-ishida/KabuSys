# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

今後の作業予定 / TODO（コードから推測）
- strategy / execution / monitoring モジュールの具体的実装（現状はパッケージ空ディレクトリ）
- 品質チェック（quality モジュール）とそのルールの詳細実装
- ETL の追加ジョブ（financials/calendar の ETL 実装完了、prices の ETL 続き）
- 単体テスト・統合テスト、CI ワークフローの整備
- ドキュメントの拡充（使用例、運用手順、DB スキーマ説明）

---

## [0.1.0] - 2026-03-17

初回リリース（コードベースから推測した機能群を実装）

### Added
- パッケージの基本構成
  - kabusys パッケージエントリ（__version__ = 0.1.0, __all__ に data/strategy/execution/monitoring を公開）
- 環境設定/読み込み機能（kabusys.config）
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env 行パーサ（export 形式、クォート、コメントの処理に対応）
  - 上書き制御（override）と保護された OS 環境変数保護機構
  - Settings クラス（J-Quants / kabu / Slack / DB パス / 環境・ログレベル検証など）
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の値チェック）と便利プロパティ（is_live 等）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベース URL とレート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）
  - リトライロジック（指数バックオフ、最大再試行回数、408/429/5xx を対象）
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ
  - pagination 対応でのデータ取得関数:
    - fetch_daily_quotes（OHLCV 日足、ページネーション対応）
    - fetch_financial_statements（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ（_to_float, _to_int）
  - 取得日時（fetched_at）を UTC で記録して Look‑ahead Bias を防止
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードの取得・パース・前処理・保存の ETL 機能
  - 安全対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - SSRF 対策（スキーム検証、プライベートIP検出、リダイレクト検査用ハンドラ）
    - 受信サイズ上限（MAX_RESPONSE_BYTES＝10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - http/https スキーム以外の URL を拒否
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証
  - テキスト前処理（URL 除去、空白正規化）
  - DuckDB への保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、新規挿入 ID リストを取得（トランザクションまとめ）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクで保存（ON CONFLICT 回避、トランザクション）
  - 銘柄コード抽出（4桁数字パターン + known_codes でフィルタ、重複除去）
  - デフォルト RSS ソース（yahoo_finance）を提供
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を想定したテーブル定義の実装
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル
  - features, ai_scores 等の Feature テーブル
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックス定義を用意
  - init_schema(db_path) でディレクトリ作成、全 DDL とインデックスを実行して初期化（冪等）
  - get_connection() による接続提供（初期化は行わない）
- ETL パイプライン（kabusys.data.pipeline）
  - ETL 設計方針に沿った実装の骨格
  - ETLResult データクラス（取得数、保存数、品質問題、エラー集約、ヘルパーメソッド）
  - テーブル存在チェック・最大日付取得ユーティリティ（_table_exists, _get_max_date）
  - 市場カレンダーを参照して非営業日を最新営業日に調整するヘルパー（_adjust_to_trading_day）
  - 差分更新ロジックのコア（last date から backfill して差分取得）
  - run_prices_etl の実装（差分算出、fetch_daily_quotes → save_daily_quotes の呼び出し）
- ロギング注釈
  - 各主要処理での情報/警告ログ出力を追加（取得件数、保存件数、スキップ件数、リトライ警告など）

### Security
- ニュース収集で複数のセキュリティ対策を実装:
  - defusedxml の採用による XML パースの安全化
  - SSRF 対策（スキーム検証、プライベート IP 検出、リダイレクト先検査）
  - レスポンスサイズ上限・gzip 解凍後チェックでリソース攻撃を軽減

### Performance / Reliability
- J-Quants クライアントでのレート制限とリトライ／指数バックオフにより API 呼び出しの安定性を向上
- DuckDB へのバルク挿入（executemany / チャンク化 / INSERT ... RETURNING）で DB 書き込みの効率化
- 冪等設計（ON CONFLICT による更新/スキップ）によりリトライや再処理に強い設計

### Notes / Known limitations
- strategy, execution, monitoring パッケージはまだ中身がない（プレースホルダ）
- quality モジュールの実装は参照されているが本コード内に定義はない（品質チェックは外部実装を想定）
- ETL の一部（例: run_prices_etl の戻り値のタプルが途中で切れている等）や追加の ETL ジョブ（financials/calendar の run_* の完成）がある可能性（コードベースから継続実装が必要）
- 単体テスト・例外パスの網羅的検証は今後の作業

---

（以降のリリースでは変更点を上に追記してください）