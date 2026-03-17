Keep a Changelog に準拠した CHANGELOG.md を日本語で作成しました。リポジトリ内のコードから推測される変更点・機能を整理し、初回リリース v0.1.0 としてまとめています。

CHANGELOG.md
=============

全般
----
- フォーマットは "Keep a Changelog" に準拠しています。
- 主要な追加・改善点、セキュリティ関連、移行手順などを記載しています。

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース。kabusys 基本モジュールを追加。
  - src/kabusys/__init__.py
    - パッケージのバージョンを `0.1.0` に設定。
    - パブリック API として data, strategy, execution, monitoring をエクスポート。

- 環境設定・読み込み機能
  - src/kabusys/config.py
    - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env 行パーサを実装し、export プレフィックス、クォート、インラインコメントの扱い等に対応。
    - Settings クラスを追加し、J-Quants/KabuStation/Slack/DBパス等のプロパティとバリデーション（KABUSYS_ENV, LOG_LEVEL 等）を提供。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API レート制御（固定間隔スロットリング: 120 req/min）を実装（_RateLimiter）。
    - リトライ機構（指数バックオフ、最大 3 回）実装。対象ステータス: 408, 429, 5xx。429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時は refresh token による id_token の自動リフレッシュを 1 回実行して再試行。
    - ページネーション対応の取得関数を提供:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (財務データ)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - DuckDB へ冪等保存する save_* 関数を実装（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 取得タイミングを追跡する fetched_at を UTC で保存。
    - 型変換ユーティリティ (_to_float, _to_int) を提供。

- ニュース収集（RSS）モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードの安全な取得と前処理機能を実装。
    - 主な機能:
      - URL 正規化（tracking パラメータ除去、クエリソート、フラグメント除去）。
      - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
      - defusedxml を使った安全な XML パース（XML Bomb 等への対策）。
      - SSRF 対策:
        - URL スキーム検証（http/https のみ許可）。
        - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検査（DNS 解決含む）。
        - リダイレクト時にスキーム・ホスト検査を行うカスタム RedirectHandler を使用。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
      - テキスト前処理（URL 除去、空白正規化）。
      - DB への保存:
        - save_raw_news: チャンク分割・トランザクション・INSERT ... RETURNING を使って新規挿入 ID を取得。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（重複除去、トランザクション）。
      - 銘柄コード抽出: 4桁数字の候補から known_codes セットでフィルタリングする extract_stock_codes。
      - 全ソース一括収集 run_news_collection を実装（ソース毎に独立してエラーハンドリング）。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の各レイヤに対するテーブル DDL を定義。
    - インデックス定義を含む（頻出クエリに合わせた複数のインデックス）。
    - init_schema(db_path) でディレクトリ作成→接続→全テーブル・インデックス作成（冪等）を実行。
    - get_connection(db_path) により既存 DB へ接続を返す（初期化は行わない）。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETL 実行結果を表す ETLResult dataclass（品質問題・エラー集約、to_dict）。
    - 差分更新ヘルパー（テーブル存在チェック、最終日取得 _get_max_date）。
    - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day)。
    - raw テーブルの最終取得日取得ユーティリティ:
      - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - run_prices_etl を実装（差分更新、バックフィル日数、J-Quants からの取得と保存のフローを担う）。品質チェック（quality モジュール）と統合する設計。

Security
- RSS パーサーに defusedxml を採用し XML 攻撃の緩和を実現。
- RSS フェッチにおける SSRF 対策を導入（スキーム制限、プライベートアドレス検査、リダイレクト検査）。
- レスポンス受信サイズ上限および Gzip 解凍後サイズチェックでメモリ DoS を緩和。
- J-Quants クライアントでの認証トークン自動リフレッシュとレート制御により不正リクエストや過負荷を低減。

Changed
- 初回リリースのため過去互換性の問題はなし。

Fixed
- 初回リリースのため既知のバグ修正履歴なし。

Notes / Usage / Migration
- 初回セットアップ:
  - DuckDB スキーマを作成するには init_schema(db_path) を呼び出してください。
  - 例: from kabusys.data.schema import init_schema; conn = init_schema("data/kabusys.duckdb")
- 環境変数例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等が Settings により必須化されています。 .env.example を参照して .env を用意してください。
  - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL:
  - run_prices_etl は差分取得ロジックと backfill を提供します（デフォルト backfill_days=3）。
  - pipeline は品質チェック quality モジュールと連携する設計になっています（quality 実装に依存）。

Known issues / TODO
- strategy/ execution / monitoring パッケージの __init__.py は現状ほぼ空であり、戦略・実行ロジックは今後実装が期待されます。
- pipeline モジュールは ETL の主要な部分を実装していますが、品質チェック処理や全体の運用ジョブ連携は別モジュール（quality 等）の実装状況に依存します。
- SQL 文の組み立てにおいて一部コードで f-string を使用している箇所があります（静的 DDL 等は問題無い想定）。動的パラメータはプレースホルダを使用していますが、将来的にセキュリティ監査を行うのが望ましいです。

Contributors
- 初回実装・設計者（リポジトリ内のコードに基づき推定）

免責
- この CHANGELOG は提供されたコードベースの内容から推測して作成したもので、実際のコミット履歴や意図とは差異がある場合があります。必要に応じて日付や細かい導入順序を調整してください。