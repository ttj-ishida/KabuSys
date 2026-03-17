Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠しています。

v0.1.0 - 2026-03-17
-------------------

Added
- パッケージ初回リリース: KabuSys — 日本株自動売買システムの基礎機能群を追加。
  - パッケージエントリポイント: kabusys/__init__.py に __version__ を追加し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定管理モジュール（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない。
  - .env 解析ロジックを実装（コメント行・export プレフィックス対応、シングル／ダブルクォート、インラインコメント、エスケープ対応）。
  - .env.local は .env より優先して既存 OS 環境変数を保護しつつ上書きできる仕組み（KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能）。
  - 環境変数読み取り用 Settings クラスを提供。J-Quants・kabu API・Slack・DB パスなどをプロパティとして公開し、値の必須チェック・バリデーション（KABUSYS_ENV、LOG_LEVEL 等）を行う。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - HTTP レート制御: 固定間隔スロットリング _RateLimiter（デフォルト 120 req/min）を導入。
  - 再試行ロジック: 指数バックオフと最大リトライ回数（デフォルト 3 回）、408/429/5xx を対象にリトライ。
  - 401 Unauthorized 受信時の自動トークンリフレッシュを 1 回まで行う仕組み（トークンキャッシュをモジュールレベルで保持しページネーション間で共有）。
  - DuckDB への保存関数 save_* を実装し、ON CONFLICT DO UPDATE による冪等性を担保（raw_prices, raw_financials, market_calendar）。
  - データ変換ユーティリティ (_to_float, _to_int) による堅牢な型変換処理を実装（空値・不正値を None として扱う、int の場合は小数部チェック）。
  - 取得時刻（fetched_at）を UTC ISO8601 で付与し、いつデータが取得されたかをトレース可能に。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードの取得・パース・前処理・DB 保存フローを実装。デフォルトソースに Yahoo Finance のビジネス RSS を登録。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML-Bomb 等に対処。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - SSRF 対策として、初回ホスト検証・リダイレクト時スキーム／ホスト検査を行う _SSRFBlockRedirectHandler を実装。プライベート/ループバック/リンクローカル/マルチキャストアドレスへの到達を拒否。
    - レスポンス受信サイズ上限（デフォルト 10 MB）と gzip 解凍後のサイズチェックを導入（メモリ DoS / Gzip bomb 対策）。
  - フィードパースと前処理:
    - content:encoded を優先、description をフォールバックとして扱う。
    - URL 除去・空白正規化等のテキスト前処理関数 preprocess_text を実装。
    - RSS pubDate の堅牢なパースと UTC 換算（パース失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news はチャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入された記事 ID リストを正確に返す（トランザクションでまとめて実行）。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けを一括挿入（重複排除、チャンク挿入、RETURNING 集計）。
  - 銘柄コード抽出ロジック extract_stock_codes（4桁数字パターンと known_codes によるフィルタ）を実装。
  - run_news_collection により複数ソースの収集を統合。各ソースは独立してエラー処理され、1 ソース失敗でも他は継続。
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（+実行レイヤ）に対応したテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル、prices_daily, market_calendar, fundamentals, news_articles 等の Processed テーブル、features / ai_scores の Feature テーブル、signals / signal_queue / orders / trades / positions / portfolio_performance の Execution レイヤを定義。
  - 適切なチェック制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を設計。
  - よく使うクエリ向けのインデックス群を追加（銘柄×日付スキャン、ステータス検索など）。
  - init_schema(db_path) によりディレクトリ作成→DDL 実行→インデックス作成までを行う初期化関数を提供。get_connection() は既存 DB への接続を返す。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を提供し、ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を収集・辞書化できる to_dict() を実装。
  - 差分更新ユーティリティ: DB の最終取得日を取得する get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - 非営業日調整ヘルパー _adjust_to_trading_day（market_calendar を参照して過去方向に最も近い営業日に調整）を実装。
  - run_prices_etl を実装（差分計算、backfill_days による再取得、jquants_client.fetch/save の呼び出し）。初回ロードではデフォルトで 2017-01-01 から取得。

Performance / Reliability
- API レート制御、リトライ、トークンキャッシュ、DB バルク挿入（チャンク化、トランザクション）の採用により、大量データ取得時の安定性とパフォーマンスを考慮。
- DuckDB 側は ON CONFLICT を多用して冪等性を担保し、再実行耐性を向上。

Security
- RSS パーサで defusedxml を使用し XML 関連攻撃に対処。
- RSS フェッチの SSRF 対策（スキーム検証、ホストのプライベート判定、リダイレクト検査）を実装。
- 外部から読み込む .env の読み込みでファイル読み込みエラーは警告を発する設計（安全側の動作）。

Notes / Limitations
- strategy, execution, monitoring パッケージはエントリーポイントとして存在するが、今回のリリースで具体的な戦略ロジック・注文実行ロジックは実装の土台（空 __init__）に留まる。
- 資格情報（API トークン等）は Settings を通じて取得し必須チェックを行うため、CI/デプロイ時に .env または環境変数の準備が必要。
- ETL の品質チェック実装（quality モジュール参照）はパイプラインに組み込む前提だが、別途 quality モジュールの具備が必要。

Acknowledgements
- 本リリースはデータ取得・保存・保護（セキュリティ）・スキーマ設計を中心に実装した初期バージョンです。今後、戦略実装・発注実行・監視・GUI/CLI 等を追加していく計画です。

-----