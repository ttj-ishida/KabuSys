# CHANGELOG

すべての注目すべき変更を記録します。本ドキュメントは「Keep a Changelog」形式に準拠します。

※この変更履歴はソースコードの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-18

追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォート有無での振る舞い差）など。
  - 必須設定取得ヘルパー _require と Settings クラスを実装:
    - J-Quants / kabuステーション / Slack / データベースパスなどのプロパティを提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証を実施。
    - duckdb/sqlite のパスは既定値を持ち Path 型で提供。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 系関数を実装。
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。
  - HTTP ユーティリティ:
    - レート制限 (120 req/min) を固定間隔スロットリングで制御する RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）を実装。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を避ける allow_refresh 制御）。
    - ページネーション対応（pagination_key を用いた連続取得）。
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes、save_financial_statements、save_market_calendar
    - fetched_at を UTC で記録（Look-ahead bias 防止の考慮）。
  - 型変換ユーティリティ _to_float / _to_int（安全に None を返す実装）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - 設計上の特徴:
    - 記事ID は正規化後 URL の SHA-256 の先頭32文字で生成し冪等性を確保。
    - defusedxml を利用して XML Bomb 等を防御。
    - HTTP リダイレクト時にスキーム/ホスト検査を行うカスタムハンドラで SSRF を軽減。
    - レスポンス最大サイズ（10 MB）や gzip 解凍後サイズ検査などでメモリDoS対策を実装。
    - トラッキングパラメータ（utm_* 等）除去、クエリソート、フラグメント削除による URL 正規化。
    - 記事本文の前処理（URL除去・空白正規化）。
    - raw_news テーブルへのバルク INSERT（チャンク化、INSERT ... RETURNING）で挿入された記事IDを正確に取得。
    - news_symbols テーブルへの銘柄紐付け（個別および一括保存関数）を実装。INSERT ... RETURNING を使用して実際に挿入された件数を返す。
    - 銘柄コード抽出機能（4桁数字）と既知銘柄リストによるフィルタリング。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリ RSS を含む。
  - run_news_collection により複数ソースを順次処理し、各ソース単位でエラーハンドリング（1ソース失敗しても継続）。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema に基づく多層スキーマ（Raw / Processed / Feature / Execution）を実装。
  - 主なテーブル:
    - raw_prices / raw_financials / raw_news / raw_executions
    - prices_daily / market_calendar / fundamentals / news_articles / news_symbols
    - features / ai_scores
    - signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ向けインデックス群を作成。
  - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成と DDL 実行を行う（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない点を明示）。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新・バックフィルの考え方に基づく ETL 実装（run_prices_etl 他の基盤実装）。
  - ETLResult dataclass を導入し、取得数・保存数・品質問題（quality モジュールの QualityIssue を想定）・エラー情報を保持。
    - to_dict により品質問題を辞書化してロギング等に利用可能。
  - 差分計算ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _get_max_date, _table_exists
  - 市場カレンダー補正ヘルパー _adjust_to_trading_day（非営業日は直近営業日に調整）。
  - run_prices_etl の差分取得ロジック（backfill_days デフォルト 3 日、初回は最小データ日付から取得）と jquants_client 連携を実装。

セキュリティ (Security)
- RSS パーシングで defusedxml を使用し XML 関連脅威を軽減。
- ニュース取得での SSRF 対策:
  - リダイレクト先のスキーム検査（http/https のみ許可）とホスト/IP のプライベート判定（IP 直接判定・DNS 解決による A/AAAA 検査）を実施。
  - 不正またはプライベートアドレス先は拒否してログに警告。
- ネットワーク周りの堅牢化:
  - J-Quants クライアント側でタイムアウト・リトライ・RateLimit を実装。

修正 (Fixed)
- 初期リリースにつき、既存バグ修正履歴なし（以下「既知の問題」に注記）。

その他 (Other)
- ロギングを各モジュールに適切に埋め込み（info/warning/exception）。
- DuckDB へのバルク挿入はチャンク化して SQL 長制限およびパラメータ数を抑制。

既知の問題 / 注意事項 (Known issues / Notes)
- run_prices_etl の末尾の return 文が未完（ソースの終端が切れているため現状の実装では (len(records), ) のように不完全な戻り値になっている可能性がある）。実運用前に戻り値タプル (fetched, saved) を正しく返すよう修正が必要。
- schema/init では DuckDB を用いるため、実行環境に duckdb パッケージが必要。
- news_collector の DNS 解決で OSError が発生した場合は安全側（非プライベート）とみなす設計だが、特殊な環境での挙動確認を推奨。
- get_id_token は settings.jquants_refresh_token に依存するため、適切な環境変数設定が必須。

開発メモ (For developers)
- 環境自動読み込みをテストする際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- RSS のテストでは news_collector._urlopen をモックしてリモートアクセスを切り替え可能に設計。
- jquants_client はモジュールレベルの ID トークンキャッシュを使用しており、ページネーション処理などでトークン共有する設計。テスト時は _get_cached_token の強制更新などを利用。

-------------------------------------------------------------------

（今後のリリースでは各機能の安定化、run_prices_etl の修正、品質チェックモジュール quality の統合、テストカバレッジ追加、ドキュメントの充実を予定）