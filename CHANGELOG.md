Keep a Changelog に準拠した CHANGELOG.md

すべての注目すべき変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]

[0.1.0] - 2026-03-18
====================

Added
-----
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
- パッケージ構成:
  - kabusys (トップパッケージ)
  - kabusys.config: 環境変数・設定管理
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサ実装（export 形式、クォート・エスケープ、インラインコメントの処理をサポート）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / システム設定（env, log_level）等のプロパティアクセスを実装。値検証（有効な env 値・ログレベル）と必須変数取得時の明示エラーを実装。
  - kabusys.data:
    - jquants_client:
      - J-Quants API クライアントを実装。株価日足、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得可能。
      - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
      - 再試行（指数バックオフ、最大3回）と HTTP ステータスに基づくリトライポリシー（408/429/5xx）。
      - 401 応答時にリフレッシュトークンから自動で id_token を更新して 1 回リトライする仕組み。
      - ページネーション対応、モジュールレベルの id_token キャッシュ、取得時刻（fetched_at）を UTC で記録（Look-ahead Bias の追跡）。
      - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を担保。
      - 型変換ユーティリティ（_to_float/_to_int）を実装し、入力の堅牢化を行う。
    - news_collector:
      - RSS フィードからニュース記事を収集し raw_news テーブルへ保存する機能を実装。
      - 記事IDは URL 正規化（トラッキングパラメータ削除・ソート・フラグメント除去・スキーム/ホスト小文字化）後の SHA-256 の先頭32文字で生成し冪等性を保証。
      - defusedxml による XML パースで XML Bomb 等の攻撃を防御。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先の事前検査（プライベート/ループバック/リンクローカル/マルチキャストを拒否）、DNS 解決結果も考慮。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）の実装、gzip 解凍時の検査（Gzip bomb 対策）、Content-Length の事前チェック。
      - RSS の pubDate パース（RFC 2822 系）とフォールバックロジック、テキスト前処理（URL 除去・空白正規化）。
      - DuckDB への保存はトランザクション内でバルク挿入し、INSERT ... RETURNING を利用して実際に挿入された ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
      - 銘柄コード抽出ロジック（4桁数字パターン + known_codes フィルタ）を実装。
      - run_news_collection により複数ソースを順次収集し、新規挿入件数と銘柄紐付けをまとめて保存するワークフローを提供。
    - schema:
      - DuckDB 用スキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
      - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤー、prices_daily 等の Processed、features / ai_scores の Feature、signal_queue / orders / trades / positions 等の Execution レイヤーを定義。
      - 適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）やインデックスを設定（頻出クエリに対するインデックス群を用意）。
      - init_schema(db_path) によりディレクトリ自動作成とテーブル初期化（冪等）を行うユーティリティを提供。get_connection() で既存 DB へ接続。
    - pipeline:
      - ETL パイプラインの基礎を実装。
      - 差分取得ロジック（DB の最終取得日を参照して未取得分のみを取得、backfill_days による後出し修正吸収）を実装。
      - ETLResult dataclass により実行結果・品質問題・エラーを集約し、監査ログや外部通知に活用可能。
      - 市場カレンダーの先読みや品質チェック（quality モジュールとの連携を想定）の枠組みを用意。
      - run_prices_etl など個別 ETL ジョブの雛形と補助ユーティリティ（_get_max_date, _table_exists, _adjust_to_trading_day, get_last_price_date 等）を実装。
- strategy / execution パッケージの __init__.py を配置し、将来的な戦略・発注機能の拡張ポイントを作成。
- パッケージの公開 API に __version__ = "0.1.0" と __all__ 指定を追加。

Security
--------
- news_collector における複数の SSRF 対策を実装（スキーム検証、プライベートホスト検査、リダイレクト検査、defusedxml の利用、受信サイズ制限）。
- jquants_client の HTTP エラーハンドリングと再試行ポリシーにより過度なリトライや不整合な挙動を抑制。

Notes / Other
-------------
- 環境変数ロードの優先順位: OS 環境変数 > .env.local > .env。
- テスト容易性のため、jquants_client の関数は id_token を外部から注入可能（モックや固定トークンでの単体テストが可能）。
- news_collector._urlopen はテスト時にモック差し替え可能な設計。
- quality モジュール（ETL 品質チェック）の具体実装は別モジュール（pipeline が参照する想定）で提供される想定。

Known limitations / TODO
-----------------------
- strategy/ execution モジュールは現時点でプレースホルダ（機能拡張のための空パッケージ）。
- ETL / pipeline の品質チェック（quality モジュール）や運用監視フローは外部実装が必要。
- 将来的に API 呼び出しの並列化や高度なレート制御（バケット方式など）を検討する余地あり。

--- 

脚注:
- 日付は本リリース時点（2026-03-18）を設定しています。必要に応じて日付を差し替えてください。