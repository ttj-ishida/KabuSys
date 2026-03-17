CHANGELOG
=========

すべての注目すべき変更を記録します。This project adheres to "Keep a Changelog" と Semantic Versioning を想定しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-17
--------------------

Added
- 初回公開リリース。パッケージ名: KabuSys（src/kabusys）。
- 環境設定管理（src/kabusys/config.py）
  - .env, .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ実装（クォート対応・export プレフィックス対応・インラインコメント処理）。
  - OS 環境変数の保護（.env.local による上書き制御、protected set）。
  - Settings クラスでアプリケーション設定を型付きプロパティで提供（J-Quants / kabu / Slack / DB パス / 環境・ログレベル検証など）。
  - 環境変数検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー取得の fetch_* 関数を実装（ページネーション対応）。
  - 認証トークン取得・キャッシュ（get_id_token / モジュールレベルキャッシュ）。
  - レート制御（固定間隔スロットリング、120 req/min を遵守）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx に対する再試行）。
  - 401 受信時の自動トークンリフレッシュ（1回まで）と再試行。
  - 取得時刻の記録（fetched_at を UTC ISO 形式で付与して look-ahead bias を低減）。
  - DuckDB への保存用 save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）：
    - 冪等性を担保（ON CONFLICT DO UPDATE）、
    - PK 欠損行のスキップ、保存件数のログ出力。
  - 型変換ユーティリティ（_to_float / _to_int）により不正値を安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードの取得（fetch_rss）と前処理、raw_news への保存（save_raw_news）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - URL スキーム検証（http/https のみ許可）および SSRF 対策（リダイレクト先のスキーム・ホスト検査）。
    - ホストがプライベートアドレスかを DNS/IP レベルで判定して内部ネットワークアクセスを拒否。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - トラッキングパラメータ除去、URL 正規化と SHA-256 ベースの記事 ID 生成（先頭32文字）で冪等性を担保。
  - テキスト前処理（URL 除去・空白正規化）。
  - DB 保存はチャンク分割・1トランザクションで実施し、INSERT ... RETURNING で新規挿入のID/件数を正確に取得。
  - 銘柄抽出ユーティリティ（4桁コードの抽出、既知銘柄セットでフィルタ）。
  - run_news_collection により複数ソースからの安全な収集と銘柄紐付けを実現。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataLayer を意識したテーブル定義を提供（Raw / Processed / Feature / Execution レイヤー）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）とインデックス定義を含む。
  - init_schema(db_path) によりディレクトリ自動作成 → テーブル／インデックス作成（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - 差分 ETL の設計・実装方針を実装（差分取得、バックフィル、品質チェックの統合）。
  - ETLResult dataclass により ETL 実行結果・品質問題・エラーを構造化して返却。
  - 市場カレンダーを考慮した trading day 調整ヘルパー。
  - テーブル最終取得日の取得ユーティリティ（get_last_price_date 等）。
  - run_prices_etl の差分ロジック（最終取得日 - backfill による date_from 自動算出）と jquants_client 経由の取得/保存ワークフローを実装（基本の流れを実装。今後の拡張点あり）。

Improved
- ロギングを各モジュールで利用し、処理状況・警告を出力するようにした（fetch/save の件数ログ、各種警告）。

Security
- RSS/HTTP の取得処理で SSRF や XML パース攻撃、圧縮爆弾を意識した防御を実装（defusedxml、ホスト/リダイレクト検査、サイズ上限、gzip 解凍後チェック）。
- .env ロード時に OS 環境変数の上書きを保護する仕組みを導入（protected set）。

Fixed
- （初版のため該当なし）

Breaking Changes
- （初版のため該当なし）

Notes / Known limitations
- strategy/execution パッケージは __init__ のみで具体的な戦略／発注ロジックは未実装。将来のリリースで追加予定。
- pipeline.run_prices_etl の戻り値実装が一部未完（ソース末尾にカンマで終わっているため、呼び出し側での利用時に調整が必要な可能性あり）。（コードベースから推測される注意点）
- quality モジュールは参照されているが本差分内に実装が含まれていないため、品質チェックを有効にするには別途実装／導入が必要。
- 現在のテスト命令は存在するが、ネットワーク依存部分は _urlopen などをモックする設計になっているため、ユニットテストの容易性を考慮している。

貢献・バグ報告
- バグ報告や提案は Issue を通じてお願いします。リリース以降に発見されたセキュリティ問題はプライベートに報告してください。