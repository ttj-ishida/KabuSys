KEEP A CHANGELOG
=================

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（開発中の変更はここに記載）

0.1.0 - 2026-03-17
------------------

初回リリース（アルファ相当）。日本株自動売買プラットフォームのコア基盤を実装しました。主な追加機能と設計方針は以下の通りです。

Added
- パッケージ骨格
  - kabusys パッケージを導入。サブパッケージとして data, strategy, execution, monitoring を公開。
  - バージョン情報: kabusys.__version__ = "0.1.0"

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードするロジックを実装（プロジェクトルートは .git / pyproject.toml から検出）。
  - .env の行パーサー（export 形式対応、クォート・コメント処理など）。
  - OS 環境変数の保護、.env と .env.local の読み込み優先度、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス、環境（development/paper_trading/live）、ログレベル等のプロパティを取得・検証。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを取得するクライアント実装。
  - レートリミッタ実装（固定間隔スロットリング、デフォルト 120 req/min を厳守）。
  - リトライ機構（指数バックオフ、最大3回、408/429/5xx 等を対象）。
  - 401 Unauthorized を検知した場合のリフレッシュトークンによる自動再取得（1回のみ）と再試行。
  - ページネーション対応で全データを取得（pagination_key を処理）。
  - DuckDB へ保存する save_* 関数は冪等性を担保（ON CONFLICT DO UPDATE）。
  - 取得時刻（fetched_at）を UTC（Z）で保存し、Look-ahead Bias を防止するためのトレーサビリティを確保。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値や空値を適切に扱う。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を取得・前処理・DuckDB へ冪等保存するパイプラインを実装。
  - セキュリティ重視の実装:
    - defusedxml を使用して XML ボム等を防御。
    - HTTP/HTTPS スキーム検証、プライベートIP/ループバック/リンクローカル/マルチキャストへのアクセスを拒否するホスト判定を実装（SSRF 対策）。
    - リダイレクト時にもスキーム/ホスト検証を行うカスタム RedirectHandler を導入。
    - レスポンスサイズ上限（10 MB）を設け、受信・gzip 解凍後ともにチェック。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - 記事IDを正規化URLの SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のパラメータ除去後に生成）。
  - テキスト前処理（URL除去、空白正規化）。
  - DuckDB への保存はチャンク化してトランザクションで実行、INSERT ... RETURNING による実際に挿入された行を返却。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン、既知コードセットでフィルタ）と記事⇔銘柄の紐付け保存機能を実装。
  - テスト容易性のため _urlopen を差し替え可能に設計。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）と頻出クエリを考慮したインデックスを追加。
  - init_schema(db_path) によりディレクトリ作成からDDL実行まで行い、冪等に初期化できる API を提供。get_connection() も実装。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスで ETL 実行結果（取得数・保存数・品質問題・エラー）を管理。
  - 差分更新ロジック補助（テーブル最終日付の取得、営業日の調整、バックフィルの考慮）。
  - run_prices_etl 等の差分 ETL ジョブ実装方針を定義（差分取得、backfill_days による再取得、品質検査モジュールとの連携）。
  - テスト容易性を考慮して id_token 注入や明示的な date_from 指定をサポート。

Security
- SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限、リダイレクト時の検証を実装。
- J-Quants クライアントでのトークンリフレッシュ時に無限再帰を防ぐための allow_refresh フラグを導入。

Changed
- 初回リリースのため該当なし。

Fixed
- ネットワーク/HTTP エラーに対して詳細なログと再試行ロジックを強化（JSON デコードエラー時に生レスポンスの一部を含めてエラーメッセージ出力など）。
- .env パーサーでのクォート内のエスケープやインラインコメント処理、export 形式への対応を実装。

Notes / Design decisions
- API レートは J-Quants の制限（120 req/min）に合わせた固定間隔スロットリングを採用。将来的にトークンバケット等に変更可能。
- DuckDB を中心に設計し、ETL は冪等性（ON CONFLICT）を重視。INSERT ... RETURNING を使うことで実際に追加された行のみを把握できるようにしている。
- ニュース収集はデフォルトで Yahoo Finance のビジネスカテゴリ RSS を推奨ソースとして設定しているが、sources 引数で任意に上書き可能。
- pipeline の品質チェック（quality モジュール）は分離し、重大度に応じた扱いを ETLResult により外部に通知する設計。

Breaking Changes
- 初版のため該当なし。ただし public API（関数/クラス名・引数）に変更が入る可能性があるため注意。

開発者向けメモ
- テスト時に .env の自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- news_collector のネットワーク呼び出しは kabusys.data.news_collector._urlopen をモックして差し替えることで容易にテスト可能です。
- jquants_client 内のトークンはモジュールレベルでキャッシュされるため、複数ページのフェッチ時に効率的に利用される設計です。

今後の予定（例）
- strategy / execution / monitoring の具体的実装（シグナル生成、注文送信ロジック、監視アラート）。
- quality モジュールの実装と ETL でのルール適用強化。
- テストカバレッジの充実と CI パイプライン整備。