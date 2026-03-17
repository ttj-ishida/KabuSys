Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

Unreleased
----------

（現在の作業ブランチ用の未リリース変更はここに記載）

[0.1.0] - 2026-03-17
-------------------

Added
- 初回公開リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ基本構成
  - モジュール群: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（各 __init__ はプレースホルダ）。
  - __version__ を src/kabusys/__init__.py に定義。
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
  - プロジェクトルート判定は .git または pyproject.toml を探索して決定（CWD 非依存）。
  - .env 行パーサ: export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、コメント処理の細かな挙動を実装。
  - Settings クラスを公開（J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の取得、バリデーション）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - データ取得: 株価日足、財務データ、マーケットカレンダーの取得関数（ページネーション対応）。
  - レートリミッタ: 固定間隔スロットリングで 120 req/min を制御（_RateLimiter）。
  - リトライ/バックオフ: 指数バックオフ、最大 3 回、対象ステータス（408, 429, 5xx）に対応。429 の場合は Retry-After ヘッダを優先。
  - 401 処理: トークン期限切れ検知で ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を担保。
  - 型変換ユーティリティ (_to_float, _to_int) を実装（空値/不正値保護、"1.0" 形式の安全な整数変換判定等）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集機能一式を実装（fetch_rss, save_raw_news, save_news_symbols, _save_news_symbols_bulk, extract_stock_codes 等）。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防ぐ。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検証、リダイレクト検査用ハンドラを実装。
    - 最大受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を設け、Gzip 解凍後も検査。
  - コンテンツ処理:
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
    - 記事 ID は正規化 URL の SHA-256 先頭32文字で生成し冪等性を保証。
    - テキスト前処理関数（URL 除去・空白正規化）。
  - DB 保存:
    - DuckDB へバルク挿入（チャンク化してトランザクションで実行）、INSERT ... RETURNING を使って実際に挿入された件数/ID を取得。
    - news_symbols の一括保存は重複除去とチャンク単位で実行。
  - 銘柄コード抽出: 4桁数字パターンから既知銘柄セットでフィルタ。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution レイヤーを想定したテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - よく使われるクエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) による自動ディレクトリ作成とスキーマ初期化を実装。get_connection() を提供。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 結果・品質問題・エラー記録を扱う。
  - 差分取得ヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）、テーブル存在チェック、最大日取得ユーティリティを実装。
  - 市場カレンダー補正ヘルパ (_adjust_to_trading_day) を実装（非営業日の場合に直近営業日に調整）。
  - run_prices_etl を追加（差分取得ロジック、バックフィル日数設定、jquants_client の fetch/save を呼び出す処理フロー）。
  - 設計メモ: 差分更新、バックフィルによる後出し修正吸収、品質チェックは Fail-Fast ではなく呼び出し元での判断を想定。
- ロギングメッセージを各モジュールで追加（INFO/WARNING/ERROR 等）。

Changed
- 初回リリースのため該当なし（新規実装）。

Fixed
- 初回リリースのため該当なし。

Security
- RSS パーサで defusedxml を利用（XML 関連脆弱性対策）。
- RSS フェッチで SSRF 対策（スキーム検証、プライベートアドレス判定、リダイレクト検査）。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を導入し、.env.local による上書きを制御。

Notes / Known issues
- run_prices_etl の現状の return 文に不備が見られます（ファイル末尾が途中で切れており、関数が (取得数, 保存数) のタプルを正しく返していない可能性があります）。本番運用前に run_prices_etl の戻り値と残りの ETL ジョブ（財務データ・カレンダー取得・品質チェック等）の実装・テストを完了してください。
- tests（ユニットテスト）や CLI / 実行用ラッパーはこのリポジトリのスナップショットに含まれていません。自動化・CI の追加、モック可能なネットワーク層の単体テスト整備を推奨します。
- NewsCollector の DNS 解決で OSError 発生時は安全側で「非プライベート」と見なす実装です（稀なケースで内部ホストを見逃す可能性があるため、必要に応じてポリシーを強化してください）。
- jquants_client は urllib を使った実装のため、並列大量リクエストや非同期処理は現状想定していません。高スループット要件がある場合は非同期化/スレッド化の検討が必要です。

References
- このリポジトリのバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に対応します。