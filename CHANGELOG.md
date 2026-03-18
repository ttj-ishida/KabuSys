CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 各リリースには Added / Changed / Fixed / Security / Known issues 等を記載します。

[Unreleased]
------------

（現時点のコードベースは初期リリースに相当します。将来の変更はここに記載します。）

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース。
  - kabusys パッケージの基本構成を追加（__init__.py にバージョン 0.1.0）。
  - モジュール群（data, strategy, execution, monitoring）をパッケージ公開（strategy/execution/monitoring はプレースホルダ）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込みを実装。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準とするため、CWD に依存しない）。
  - .env と .env.local の優先順位と override / protected（OS 環境変数保護）動作を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env 行パーサー強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無での挙動差）に対応
  - Settings クラスを公開し、アプリ設定（J-Quants、kabu API、Slack、DBパス、環境種別、ログレベル等）をプロパティで提供。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許可値チェック）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回再試行。
    - ページネーション対応（pagination_key）。
    - id_token のモジュールレベルキャッシュによりページ間でトークン共有。
  - 高レベル API:
    - get_id_token(): リフレッシュトークンから id_token を取得（POST）。
    - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar(): データ取得（ページネーション対応）。
  - DuckDB への保存ヘルパー:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar(): 冪等保存（ON CONFLICT DO UPDATE）。
    - 保存時に fetched_at を UTC ISO8601（Z）で記録。
    - PK 欠損レコードはスキップして警告ログ出力。
  - 入力パース用ユーティリティ: _to_float(), _to_int()（堅牢な数値変換）。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news / news_symbols に保存する処理を実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を使った XML パース（XML Bomb 等の防御）。
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時にスキームとホストを検査する SSRF 防止ハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカルであれば接続禁止。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の再チェック。
    - Content-Length の事前チェック（不正値は無視）。
  - フィード処理:
    - URL 正規化（トラッキングパラメータ削除、クエリ並べ替え、フラグメント削除）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパースと UTC への正規化（パース失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news(): INSERT ... RETURNING を用いて、実際に挿入された記事 ID のリストを返す。チャンク挿入と 1 トランザクション実行。
    - save_news_symbols() / _save_news_symbols_bulk(): news_symbols の一括保存（重複除去、チャンク挿入、INSERT ... RETURNING による正確な挿入数取得）。
  - 銘柄コード抽出: 4 桁数字パターンから既知銘柄セットにマッチするものだけを抽出（重複除去）。
  - run_news_collection(): 複数ソースを独立して処理し、各ソースの成功件数を返す。known_codes を渡すと新規記事に対して銘柄紐付けを実行。
- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores（Feature レイヤー）。
  - signals, signal_queue, orders, trades, positions, portfolio_performance（Execution レイヤー）。
  - 適切なチェック制約（CHECK）、主キー、外部キー、インデックス定義を用意。
  - init_schema(db_path): DB ファイル親ディレクトリ自動作成、全テーブル/インデックスを冪等で作成して DuckDB 接続を返す。
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass により ETL の統計・品質問題・エラーを集約。
  - 差分更新ヘルパー:
    - DB 最終取得日の取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 営業日への調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl(): 差分更新（最終取得日 - backfill_days から再取得）を行い、jquants_client 経由で取得・保存するワークフローを実装（バックフィルデフォルト：3日）。
  - ETL の設計方針:
    - 後出し修正を吸収するためのバックフィル、
    - 品質チェック（quality モジュール）を呼び出し、問題の重大度に応じた情報を ETLResult に保持（Fail-Fast しない）。

Changed
- N/A（初期リリースのため履歴変更はなし）。

Fixed
- N/A（初期リリース）。

Security
- RSS 処理における複数のセキュリティ対策を導入（defusedxml、SSRF 対策、レスポンスサイズ制限、URL スキーム検証等）。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を採用。

Performance
- J-Quants API 呼び出しに RateLimiter を導入してレート制限を遵守。
- ニュース保存はチャンク化（_INSERT_CHUNK_SIZE=1000）してバルク INSERT を行い、トランザクションをまとめてオーバーヘッドを削減。
- DuckDB 側に多くのインデックスを作成し、頻出クエリパターンのスキャンを最適化。

Known issues / Notes
- run_prices_etl の戻り値に関して:
  - ドキュメントでは (取得数, 保存数) を返すとあるが、現在の実装では関数末尾の return が "return len(records)," のように単一要素タプルになっており、保存件数を返していない（実装バグの疑い）。次版で修正が必要。
- quality モジュール参照:
  - pipeline は品質チェック用に kabusys.data.quality を参照しているが、この品質チェックモジュール本体は本差分に含まれていない（別途実装が必要）。
- strategy / execution / monitoring モジュール:
  - パッケージ公開名として存在するが（__all__ に含まれる）、現状は空のパッケージ/プレースホルダとなっている。これらは今後の実装対象。
- NEWS 抽出の既知銘柄リスト:
  - extract_stock_codes() は known_codes セットを引数に取る仕様のため、実運用では有効銘柄一覧（リストまたはテーブル）を別途供給する必要がある。

Migration notes
- init_schema() は既存テーブルがあればスキップするため、既存 DB に対する安全な初期化が可能。
- .env 読み込みはデフォルトで有効。CI/テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements / Implementation decisions
- API の堅牢性（再試行・トークン自動更新・レート制御）や RSS 処理のセキュリティ（defusedxml・SSRF 対策・レスポンス上限）は特に注意して設計しています。
- DuckDB を中心としたデータレイヤ設計（Raw / Processed / Feature / Execution）の採用により、ETL と分析／戦略ロジックの分離を図っています。

今後の予定
- pipeline の品質チェック（quality モジュール）実装と統合。
- strategy / execution / monitoring モジュールの具体実装。
- run_prices_etl の戻り値バグ修正と追加の単体テストの整備。
- テストカバレッジ向上（特にネットワーク周りと XML パース、SSRF ハンドリング）。
- ドキュメント（DataPlatform.md, API 使用例、運用ガイド）の充実。

---