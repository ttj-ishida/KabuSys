CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

[unreleased]
-------------

（現在のコードベースに未リリースの差分はありません）

[0.1.0] - 2026-03-17
-------------------

初期リリース（ベース機能の実装）

追加
- パッケージ基盤
  - パッケージのバージョンを 0.1.0 として公開（kabusys.__version__）。
  - 公開モジュール: data, strategy, execution, monitoring（パッケージエントリポイント定義）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env の export 形式・クォート・インラインコメント等に対応するパーサー実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / システム設定をプロパティ経由で取得。
    - 必須環境変数未設定時に明示的な例外を投げる _require() を備える。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値セット）を実装。
    - duckdb/sqlite のデフォルトパス取得（Path による展開）。
- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - API レート制御（120 req/min）のための固定間隔スロットリング RateLimiter を導入。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）を実装。
    - 401 応答時の ID トークン自動リフレッシュ（1 回）をサポート。
    - ページネーション対応で fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）を行う save_* 関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - データ取得時刻（fetched_at）を UTC ISO 形式で記録して look-ahead bias のトレースを容易に。
    - 型変換ユーティリティ（_to_float, _to_int）を提供。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを取得し raw_news に保存する機能を実装。
    - RSS 解析に defusedxml を利用して XML Bomb 等の攻撃に対処。
    - HTTP レスポンスの受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を導入しメモリ DoS を防止。
    - gzip 圧縮対応と、解凍後のサイズチェック（Gzip bomb 対策）。
    - リダイレクト時の SSRF 検査ハンドラ（_SSRFBlockRedirectHandler）とホストプライベート判定を実装。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）を提供。
    - DB 保存はトランザクション・チャンク処理で行い、INSERT ... RETURNING により新規挿入分の ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - 銘柄コード抽出ロジック（4桁数字の抽出と known_codes によるフィルタ）を提供。
    - 全ソースをまとめて収集・保存する run_news_collection ジョブを提供（ソース毎にエラーハンドリング）。
- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema に基づく DuckDB テーブル群を定義 & 初期化する init_schema 関数を実装。
    - Raw / Processed / Feature / Execution の各レイヤーのテーブル DDL を備える（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 性能想定に基づくインデックス定義を含む。
    - :memory: を使ったインメモリ DB にも対応。
    - 既存ディレクトリがなければ自動で作成。
- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針に沿った差分更新パイプラインの骨格を実装。
    - ETLResult データクラス（品質問題やエラーの収集、結果辞書化機能を提供）。
    - DB の最終取得日を取得するヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 取引日補正ヘルパー（_adjust_to_trading_day）。
    - run_prices_etl（差分取得・backfill・保存の流れ）を実装（差分計算、jquants_client 呼び出し、保存、ログ記録）。
    - backfill_days による後出し修正吸収の仕組みを導入。
- 型注釈・ログ
  - 主要関数に型ヒントを付与し、ログ出力（logger）を適所で追加。

セキュリティ
- SSRF 対策
  - ニュース収集でのリダイレクト先検査、ホストのプライベート/ループバック判定、非 http/https スキームの拒否を実装。
  - XML パースに defusedxml を使用し XML 関連脅威に対応。
- リソース制限
  - RSS レスポンス最大バイト数制限と gzip 解凍後のサイズ検証で DoS に対処。

変更
- （初回リリースのため過去バージョンからの変更はなし）

修正
- （初回リリースのため過去バージョンからの修正はなし）

破壊的変更
- なし

注記 / 今後の課題（コードから推測）
- ETL の品質チェック（quality モジュール）との連携箇所は仕組みを想定しているが、quality の実装次第で動作が変わる可能性がある。
- strategy・execution・monitoring パッケージはエントリを用意しているが、各サブモジュールの実装はパッケージ骨格の段階に留まる可能性がある（将来の拡張想定）。
- run_prices_etl の戻り値はコード末尾で途中に見切れている箇所があるため、実装の完成・戻り値仕様確認が必要（コードベースからの推測による記述）。

著者・連絡
- この CHANGELOG はリポジトリ内のコード構成から推測して自動生成されました。細かな実装意図や追加・修正履歴がある場合は、適宜補正してください。