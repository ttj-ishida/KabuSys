Keep a Changelog準拠の CHANGELOG.md を日本語で作成しました。初回リリース v0.1.0 として、実装済みの機能・設計方針・注意点（既知の問題）をコードベースから推測してまとめています。

CHANGELOG.md
=============

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ基本構成
  - kabusys パッケージの初期モジュールを追加（__version__ = "0.1.0"）。
  - サブパッケージのプレースホルダ: data, strategy, execution, monitoring.

- 環境設定/ローディング (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない。
  - .env のパースは export 形式・クォート処理・インラインコメント等に対応。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ ログレベル等の取得を提供。必須キー未設定時は例外を投げる。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、四半期財務、マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - 認証: リフレッシュトークンから id_token を取得する get_id_token を実装。401 を受けた場合は自動リフレッシュして1回リトライ。
  - レート制限: 固定間隔スロットリング（120 req/min）を守る _RateLimiter を実装。
  - 再試行: 指数バックオフを用いたリトライロジック（最大3回）。408/429/5xx をリトライ対象に設定。429 の Retry-After を優先利用。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等（ON CONFLICT DO UPDATE）で保存。
  - データ取得時刻（fetched_at）を UTC ISO 形式で記録し、look-ahead bias をトレース可能に。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事収集を行う fetch_rss / run_news_collection を実装。
  - セキュリティ対策:
    - defusedxml を使った XML パースで XML Bomb 等に対処。
    - SSRF 対策としてリダイレクト前後のスキーム検証およびプライベートアドレス検査（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキームは http/https のみ許可。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入。gzip 解凍後もサイズチェックを実施。
  - 追跡パラメータ除去・URL 正規化（utm_* 等を除去）、SHA-256（先頭32文字）ベースの記事ID生成により冪等性を保証。
  - テキスト前処理（URL 除去・空白正規化）を実装。
  - DuckDB へはトランザクション内でバルク INSERT を行い、ON CONFLICT DO NOTHING と INSERT ... RETURNING によって実際に挿入された記事IDや件数を正確に取得する（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ロジック（4桁数字と known_codes の照合）を提供。

- スキーマ定義 / 初期化 (kabusys.data.schema)
  - DuckDB 用の包括的スキーマを実装（Raw / Processed / Feature / Execution レイヤ）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 頻出クエリのためのインデックス群も作成。
  - init_schema(db_path) でディレクトリ自動作成・DDL 実行・接続を返す。get_connection(db_path) も提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - 差分更新を行う ETLResult データクラスを実装（品質チェック結果・エラー一覧を保持）。
  - DB の最終取得日を取得するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 価格 ETL の差分更新ロジック（run_prices_etl）を追加: 最終取得日に基づいた date_from 自動算出（バックフィル期間を指定可能）、J-Quants からの取得と save_* による冪等保存を実行。
  - 日付/市場カレンダー関連ユーティリティ（_adjust_to_trading_day）を実装。
  - ETL 設計方針として backfill（デフォルト3日）により API の後出し修正に耐性を持たせる、品質チェックはエラーがあっても処理を続行する方針を採用。

Security
- RSS 収集における SSRF 対策、defusedxml の利用、受信サイズ制限など複数のセキュリティ対策を導入。
- 環境変数の読み込みで OS 環境を保護するための protected 機能を実装（.env の上書き制御）。

Notes / Implementation details
- テスト用フック:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env 読み込み停止。
  - news_collector._urlopen はテストでモックして差し替え可能。
  - jquants_client の id_token はモジュールレベルのキャッシュを利用し、force_refresh で再取得可能。
- DB 操作は可能な限り冪等化（ON CONFLICT）しており、INSERT ... RETURNING を活用して実際に挿入された行だけを数える設計。

Fixed
- なし（初期リリース）

Changed
- なし（初期リリース）

Deprecated
- なし（初期リリース）

Removed
- なし（初期リリース）

Known issues / TODO
- run_prices_etl の戻り値
  - 現在の実装では run_prices_etl の終端に "return len(records)," のように単一値を末尾のカンマ付きで返しており、関数注釈で期待される (int, int) のタプルを満たしていません。テスト・利用時に戻り値の構造を確認し、(fetched_count, saved_count) の形式で返すよう修正が必要です。
- pipeline モジュールは prices_etl の部分実装が含まれているものの、財務データ/カレンダーの個別 ETL の統合的な実行・品質チェックフロー（quality モジュールとの連携）や監査ログ出力などは今後の実装想定。
- エラーハンドリングやメトリクス（監視/アラート）を強化するための監視モジュール実装が未着手（monitoring パッケージの実装はプレースホルダのみ）。

Security
- ニュース収集・HTTP周りの実装は SSRF や大容量レスポンス対策を含みますが、運用環境での振る舞い確認（DNS 解決ポリシー、プロキシ下での動作、タイムアウト設計など）は推奨されます。

その他
- 初期リリースのため、API の安定化・リファクタリング・ユニットテストの整備・ドキュメント拡充が今後の課題です。

（この CHANGELOG はコードから推測して作成しています。実際のリリースノートや運用上の注記と合わせてご利用ください。）