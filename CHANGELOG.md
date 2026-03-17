CHANGELOG
=========

すべての注目すべき変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。
リリース日はコードベースのスナップショット（推定）に基づいて付与しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージ初期化: src/kabusys/__init__.py にて基本 __version__ と公開モジュールを定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml から探索、優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パースの堅牢化:
    - export プレフィックス対応、クォート済み値のバックスラッシュエスケープ対応、インラインコメント処理。
  - Settings クラス:
    - J-Quants / kabu / Slack / DB パス等のプロパティを提供（必須環境変数は未設定時に ValueError を送出）。
    - KABUSYS_ENV / LOG_LEVEL の値検証、 is_live/is_paper/is_dev の補助プロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 通信の共通処理を実装（_request）。
    - レート制限 (120 req/min) を固定間隔スロットリングで実施（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時は自動で id_token をリフレッシュして 1 回リトライ（無限再帰防止フラグあり）。
    - JSON デコードエラー時の明確な例外メッセージ。
  - トークン取得ヘルパー get_id_token（refresh トークンから idToken を取得）。
  - データ取得関数:
    - fetch_daily_quotes（ページネーション対応で株価日足取得）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー取得）
    - 各取得で取得件数のログ出力、ページネーションキー重複チェック
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - fetched_at は UTC で記録し Look-ahead Bias のトレースを可能に
    - INSERT ... ON CONFLICT DO UPDATE により冪等保存

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集処理の実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection 等）。
  - セキュリティおよび堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベートアドレスか判定して拒否、リダイレクト先検査用ハンドラ実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策、gzip 解凍後サイズ再検査。
  - データ処理/正規化:
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性保証）。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパースと UTC 正規化（パース失敗時は代替時刻を採用）。
  - DB 書き込み:
    - bulk INSERT をチャンク化して 1 トランザクションで実行、INSERT ... RETURNING を用いて実際に挿入された ID を返す。
    - news_symbols の一括保存用内部関数（重複除去、チャンク化）を実装。
  - 銘柄コード抽出ユーティリティ（4 桁数字パターン + known_codes フィルタ）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataLayer に沿ったテーブル定義を実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約と型チェック（NOT NULL / CHECK 等）を多用してデータ整合性を担保。
  - 頻出クエリ向けインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行・接続返却（:memory: 対応）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー集約）。
  - テーブル存在チェック、最終取得日の取得ユーティリティ。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新方針の実装方針（backfill_days による後出し修正吸収）。
  - run_prices_etl の実装（差分判定、fetch -> save の一連の流れ）を追加。
  - quality モジュールとの連携を想定した設計（品質チェックの重大度処理や集約）。

Security
- RSS / HTTP 処理に関する SSRF 対策の導入（スキーム検証、プライベート IP 拒否、リダイレクト検査）。
- XML パースに defusedxml を使用し、外部攻撃を低減。
- 外部 API 呼び出しでのレート制限と再試行ロジックを導入し、サービス過負荷や 429 への対処を実装。

Notes / Known issues
- pipeline.run_prices_etl の返り値処理がコードスナップショット末尾で途中のように見える箇所がある（保存件数を返却する部分の完了が欠落している可能性）。実運用前に戻り値とエラーハンドリングの最終確認を推奨。
- テスト・CI に関するコードやモック実装（例: HTTP モック用の抽象化）は最小限に留められているため、網羅的なユニットテストの整備が推奨される。
- Slack / kabu ステーション周りの実際の実行ロジック（execution/monitoring/strategy の具象実装）はパッケージ構成に名前空間があるが、本スナップショットでは未実装（将来的な拡張ポイント）。

Authors
- 本 CHANGELOG は提供されたコードベース（src/ 以下の実装）から推測して作成しました。実際のコミット履歴がある場合はそちらを優先してください。