CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/),
and follows Semantic Versioning.

[Unreleased]
------------

- なし

0.1.0 - 2026-03-18
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。
  - 環境設定管理 (kabusys.config)
    - .env/.env.local からの自動読み込み機能を実装（優先順位: OS 環境 > .env.local > .env）。
    - .env パーサーは export 形式、クォート付き値、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みの無効化が可能。
    - Settings クラスを提供し、J-Quants や kabu API、Slack、DB パス、実行環境（development/paper_trading/live）やログレベルのバリデーションを行うプロパティを実装。
  - J-Quants クライアント (kabusys.data.jquants_client)
    - API 呼び出し時の固定間隔レートリミッタ（120 req/min）。
    - 冪等性と堅牢性を考慮した HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - id_token のモジュールレベルキャッシュを保持し、ページネーション間で共有。
    - ページネーション対応のデータ取得関数を追加:
      - fetch_daily_quotes（OHLCV）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等）を提供:
      - save_daily_quotes（raw_prices テーブル、ON CONFLICT DO UPDATE）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 数値変換ユーティリティ _to_float/_to_int を実装（入力の許容範囲と変換失敗時の扱いを明確化）。
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードから記事を収集する fetch_rss を実装（デフォルトソースに Yahoo Finance）。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb や類似攻撃対策）。
      - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバックでないことの検査、リダイレクト先検証用のカスタム RedirectHandler。
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - HTTP/HTTPS 以外のスキームを拒否。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭32文字）を実装し冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を用いたチャンク単位挿入（挿入された新規記事 ID を返す）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンクで保存（ON CONFLICT DO NOTHING / INSERT RETURNING）。
    - 銘柄抽出: 4桁数字パターンに基づく extract_stock_codes を実装（既知コードセットでフィルタ、重複除去）。
    - 統合ジョブ run_news_collection を追加（複数ソースを個別に処理し、失敗しても他ソースを継続）。
  - DuckDB スキーマ (kabusys.data.schema)
    - Raw / Processed / Feature / Execution 層を含むデータベーススキーマを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - 各テーブルの制約（PRIMARY KEY / FOREIGN KEY / CHECK）を設定。
    - よく使うクエリのためのインデックスを作成。
    - init_schema(db_path) によりディレクトリ作成・テーブル作成を行い DuckDB 接続を返す。get_connection で既存 DB に接続可能。
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - スキーマ/テーブル存在チェックや日付最大値取得のユーティリティを実装。
    - 市場カレンダーのトレーディング日調整ヘルパー（_adjust_to_trading_day）。
    - 差分更新方針を取り入れた run_prices_etl を追加:
      - DB の最終取得日を元に差分（および backfill_days 分の再取得）を決定し、fetch_daily_quotes → save_daily_quotes を実行する。
    - 既存の quality モジュール呼び出しを想定した設計（品質チェックのための構造を準備）。
  - その他
    - 各モジュールで適切な logger 呼び出しを追加し、実行ログを記録。
    - duckdb を DB エンジンに採用し、トランザクション制御や INSERT ... RETURNING を活用することで正確な挿入件数集計を実現。

Security
- XML パースは defusedxml を利用し安全化。
- RSS フェッチ周りで SSRF・Gzip bomb・大容量レスポンス対策を実装。
- .env の読み込みでは既存 OS 環境の保護（protected セット）を考慮した上書き挙動を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes
- ETL パイプラインは価格データの差分取得（run_prices_etl）を中心に実装済み。財務データやカレンダーの ETL ジョブ、品質チェックとの統合は継続して実装予定。
- quality モジュールや strategy / execution / monitoring の具象実装は、このバージョンでは参照や骨組みが中心。今後のリリースで機能追加予定。
- コード内の一部関数はユニットテスト用に外部置換（モック）を想定した設計になっている（例: news_collector._urlopen）。

Notes for developers
- 環境変数が不足していると Settings のプロパティは ValueError を発生させます（必須値: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- データベース初期化は init_schema() を用いること（get_connection() はスキーマ初期化を行わない）。
- J-Quants の API レート制限とリトライ挙動は jquants_client に集約されているため、外部から id_token を注入してテスト可能。

License
- このプロジェクトのライセンス情報はリポジトリのルートに従うこと。

---