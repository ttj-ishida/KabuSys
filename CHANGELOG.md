CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Security, etc.）に分けて記載しています。
- バージョンごとに日付を記載しています（YYYY-MM-DD）。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース (0.1.0)
  - パッケージ基盤: kabusys パッケージを公開（__version__ = 0.1.0）。パッケージは data, strategy, execution, monitoring をエクスポート。
- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
  - プロジェクトルートの検出: __file__ から親ディレクトリを探索し、.git または pyproject.toml を基準にルートを特定。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - .env 自動ロードの制御: KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - Settings クラスを実装し、主要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV 値チェック（development, paper_trading, live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）とユーティリティプロパティ is_live / is_paper / is_dev
- J-Quants API クライアント (kabusys.data.jquants_client)
  - API クライアントを実装。主な機能:
    - レート制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回のみ再試行。
    - ページネーション対応（pagination_key を順次追跡）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE による冪等性）。
    - 取得時刻（fetched_at）を UTC タイムゾーンで記録して look-ahead bias を抑制。
    - 型変換ユーティリティ (_to_float, _to_int) を提供。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集する一連の実装:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - プライベート/ループバック/リンクローカル/マルチキャスト IP の検出と拒否。
      - リダイレクト時に事前検証を行うカスタム RedirectHandler を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の検査（Gzip bomb 対策）。
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - テキスト前処理: URL 除去・空白正規化。
    - DB 保存:
      - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す（トランザクションでまとめる）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT で重複排除、INSERT ... RETURNING を活用して実挿入数を取得）。
    - 銘柄コード抽出ロジック: 4桁数字パターンを候補とし、known_codes セットでフィルタする extract_stock_codes を提供。
    - run_news_collection: 複数ソースを順次処理し、ソース単位で独立したエラーハンドリングを行う統合ジョブを実装。
- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の各レイヤーのテーブル DDL を実装。
  - テーブル・制約・インデックスを定義（主キー、チェック制約、外部キー、よく使う検索のためのインデックス）。
  - init_schema(db_path) によりディレクトリ作成→DDL 実行→インデックス作成を行い、DuckDB 接続を返す。
  - get_connection(db_path) を実装（初回スキーマ初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（差分取得）と保存フローの骨格を実装:
    - ETLResult dataclass により ETL 結果、品質問題、エラー一覧を構造化。
    - 最終取得日の取得ユーティリティ（_get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダー補助: 非営業日の調整ロジック (_adjust_to_trading_day)。
    - run_prices_etl: 差分算出（backfill_days デフォルト 3）→fetch_daily_quotes→save_daily_quotes を行うジョブの実装（差分更新の方針を反映）。

Changed
- （初回公開のため該当なし）

Fixed
- （初回公開のため該当なし）

Security
- ニュース収集における SSRF 対策を実装（スキーム検証、プライベートアドレス検査、リダイレクト検査）。
- XML パースに defusedxml を使用して XML 関連の脆弱性に対処。
- レスポンスサイズ制限と gzip 解凍後のチェックによりメモリ消費攻撃を緩和。

Known issues / Notes
- run_prices_etl の末尾での return 文が不完全に見える箇所があり（ソースの切り出し時点での実装断片）、戻り値の型や呼び出し側との整合性に注意が必要です（小修正が必要になる可能性があります）。
- 一部モジュール（strategy, execution, monitoring）の __init__.py は空のプレースホルダとなっており、各レイヤーの実装は今後追加予定です。
- schema の DDL は現状で包括的なテーブル設計を含みますが、運用・クエリ実績に応じてインデックスやパーティショニング方針の見直しが想定されます。
- J-Quants クライアントは urllib を使った同期実装。高スループット・非同期化が必要な場合は別途リファクタリングが推奨されます。

作者 / 貢献者
- コードベース（初期実装）に基づく自動生成の変更履歴（本ファイルはコード内容から推測して作成）。

ライセンス
- （コードリポジトリのライセンス表記に従ってください。ここでは明示していません。）

-- end of CHANGELOG --