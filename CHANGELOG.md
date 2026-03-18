CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の形式に準拠しています。

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期実装（__version__ = 0.1.0、主要サブパッケージを __all__ に公開: data, strategy, execution, monitoring）。
- 環境設定 / 設定管理
  - .env ファイルおよび環境変数からの設定読み込み機能を追加（src/kabusys/config.py）。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を基準）。これによりワーキングディレクトリに依存せず自動ロードを行う。
  - .env と .env.local の自動読み込み（優先度: OS 環境 > .env.local > .env）。既存 OS 環境を保護する protected 機能を実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサー実装:
    - export プレフィックス対応、シングル/ダブルクォート処理（バックスラッシュエスケープ考慮）、インラインコメントの扱い、コメント判定ルール等を実装。
  - Settings クラスを実装し、以下の設定項目をプロパティで取得可能に:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足、財務データ、マーケットカレンダー取得用の fetch_* 関数を実装（ページネーション対応）。
  - リクエスト送信ユーティリティを実装。機能:
    - 固定間隔レート制御（120 req/min を満たす _RateLimiter）
    - 再試行（最大 3 回、指数バックオフ）およびステータスによる制御（408, 429, >=500 をリトライ対象）
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有（モジュールレベル）
    - JSON デコードエラー時の詳細エラーメッセージ
  - DuckDB 保存用の save_* 関数を実装（冪等性を担保する ON CONFLICT DO UPDATE を使用）。fetched_at は UTC ISO 形式で記録。
  - 型変換ユーティリティ _to_float / _to_int を実装。_to_int は "1.0" のような表現を float 経由で整数へ変換するが、小数部が非ゼロの値は None を返す仕様。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事収集し raw_news へ保存するフローを実装。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - SSRF 対策: リダイレクト時にスキーム/ホストを検査する独自ハンドラ(_SSRFBlockRedirectHandler)、URL スキーム検証、ホストがプライベート/ループバックでないことのチェック。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - HTTP/HTTPS 以外の URL を拒否。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
  - 記事 ID を正規化 URL の SHA-256 先頭32文字で生成し冪等性を担保。
  - テキスト前処理関数 preprocess_text（URL除去、空白正規化）を追加。
  - pubDate の RFC2822 パースと UTC への正規化を実装（失敗時は警告ログと代替時刻）。
  - DuckDB への保存:
    - save_raw_news: チャンク化・トランザクション・INSERT ... RETURNING による新規挿入 ID の取得を実装。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入し、実際に挿入された件数を返す実装。
  - 銘柄抽出機能 extract_stock_codes（4桁数字の抽出と既知コードセットによるフィルタリング）を実装。
  - run_news_collection で複数ソースを巡回し、エラーが起きても他ソースを継続する堅牢なジョブ処理を追加。
- スキーマ定義 / DB 初期化（src/kabusys/data/schema.py）
  - DuckDB の DDL を実装（Raw / Processed / Feature / Execution レイヤー）。
  - 各テーブルに制約（PK, FK, CHECK）を付与。
  - 頻用クエリに対するインデックスを定義。
  - init_schema(db_path) でディレクトリ作成・すべてのテーブルとインデックスを冪等に作成する API を提供。get_connection は既存 DB への接続を返す。
- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧等を保持、辞書化メソッド含む）。
  - テーブル存在確認、最大日付取得ヘルパー（_table_exists / _get_max_date）、営業日調整ロジック(_adjust_to_trading_day) を実装。
  - 差分更新方針: 最終取得日から backfill_days 日前を再取得して API の後出し修正を吸収するデフォルト挙動を実装。
  - run_prices_etl の骨組み（差分計算、fetch + save の呼び出し）を実装（取得→保存→ログ出力まで）。
- その他
  - ロギングメッセージを多用し、処理の可観測性を確保（各モジュールで info/warning/exception を適切に出力）。

Security
- RSS 収集での SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ上限の導入により外部入力による攻撃耐性を強化。
- .env 読み込み時に OS 環境を保護する protected キー概念を導入し、意図しない上書きを防止。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Known issues
- 一部の関数は骨組みやヘルパーのみ実装されており、運用面の詳細（例: quality モジュールの品質チェックルール、strategy / execution / monitoring の具象実装）はこのバージョンでは提供されていません。
- run_prices_etl はファイル末尾で切れている（トランケートの可能性）。実行時に追加のロジックが必要な場合があります。
- J-Quants のレート制限や API 仕様変更、また DuckDB の SQL 構文差異に依存するため、本番環境での動作確認を推奨します。

参考
- バージョニング: セマンティックバージョニングに従い、現行は 0.1.0（初期リリース）。今後の変更は Breaking / Added / Fixed を明確に分けて追記します。