CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン表記はパッケージ内の __version__ に合わせています。

[Unreleased]
-------------

- （現時点なし）

[0.1.0] - 2026-03-17
--------------------

Added
- 初版リリース: KabuSys — 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数/設定管理（.env 自動読み込み、保護済み OS 環境変数処理、必須チェック付き Settings クラス）。
    - kabusys.data:
      - jquants_client: J-Quants API クライアント（株価日足、財務データ、JPX マーケットカレンダー取得、ページネーション対応、DuckDB への冪等保存）。
      - news_collector: RSS ベースのニュース収集（RSS パース、前処理、記事ID生成、銘柄コード抽出、DuckDB への保存）。
      - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 各レイヤーのテーブル、インデックス、外部キー）。
      - pipeline: ETL パイプライン基盤（差分更新ロジック、バックフィル、品質チェックフック用の ETLResult）。
    - kabusys.strategy, kabusys.execution, kabusys.monitoring: 名前空間を公開（モジュール初期化ファイルを配置）。
  - パッケージメタ情報: __version__ = "0.1.0"

- 環境設定周りの機能:
  - プロジェクトルート自動検出（.git または pyproject.toml を基準に探索）により CWD 非依存で .env を読み込み。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
  - .env パーサは export 形式やクォート、インラインコメント、エスケープに対応。

- J-Quants API クライアント（jquants_client）:
  - レート制限管理（固定間隔スロットリング、デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429 と 5xx を対象）。
  - 401 受信時の自動 id_token リフレッシュ（1 回のみ）とトークンキャッシュ（ページネーション間で共有）。
  - fetch_* 系関数はページネーション対応（pagination_key）で全件取得。
  - 保存関数は DuckDB に対して冪等的に保存（INSERT ... ON CONFLICT DO UPDATE）、fetched_at を UTC で記録。

- ニュース収集（news_collector）:
  - RSS から記事を収集し raw_news テーブルへ保存（INSERT ... RETURNING で新規挿入 ID を取得）。
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成しトラッキングパラメータ（utm_* 等）を除去して冪等性を確保。
  - defusedxml を利用した XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時にスキームと宛先ホストの検証を行うカスタム RedirectHandler を使用。
    - ホストがプライベート / ループバック / リンクローカル / マルチキャストであれば拒否（IP 直接判定 + DNS 解決で A/AAAA を検査）。
  - レスポンスサイズ上限（デフォルト 10 MB）と gzip 解凍後のサイズチェックでメモリ DoS を防止。
  - テキスト前処理（URL 除去・空白正規化）と既知銘柄集合を使った 4 桁銘柄コード抽出機能。
  - 銘柄紐付けは一括 INSERT をトランザクションで実行し実際に挿入された件数を正確に返却。

- DuckDB スキーマ（schema）:
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義を追加（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 適切な PRIMARY KEY、CHECK 制約、FOREIGN KEY、インデックス定義を含む。
  - init_schema(db_path) によりディレクトリ作成からテーブル作成まで冪等に初期化可能。get_connection() で既存 DB に接続。

- ETL パイプライン（pipeline）:
  - 差分更新を行うヘルパー（最終取得日取得、営業日調整、backfill の仕組み）。
  - ETL 実行結果を表す ETLResult dataclass（品質問題・エラー集約、辞書化メソッド）。
  - run_prices_etl 等の個別 ETL ジョブの雛形（差分取得→保存→品質チェックの流れを実装）。

Changed
- （初版のため該当なし）

Fixed
- データ変換ユーティリティの注意点を明示:
  - _to_float/_to_int は不正値や空値を None に変換し、安全にパースする（"1.0" のような float 文字列は float 経由で整数に変換し、小数部が残る場合は None を返すことで意図しない切り捨てを防止）。

Security
- 複数の防御策を導入:
  - RSS XML パースに defusedxml を使用して XML ベースの攻撃を緩和。
  - RSS フェッチ時の SSRF 対策（URL スキーム検証、リダイレクト先チェック、プライベートホスト拒否）。
  - レスポンス上限（MAX_RESPONSE_BYTES）と gzip 解凍後の再チェックでメモリ消費攻撃を防止。
  - .env 自動ロード時に OS 環境変数を保護（.env による上書きを制御）し、不正な環境汚染を防ぐ。

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Notes / Known issues
- pipeline.run_prices_etl の実装ファイル断片（提供されたコードスニペット末尾）が途中で終わっており、戻り値や一部ロジックが完全に示されていないように見受けられます。実運用前に run_prices_etl が (fetched_count, saved_count) を正しく返すこと、及び品質チェックとの連携が期待どおり動作することを確認してください。
- 今後の改善候補（未実装/拡張余地）:
  - NewsCollector のフィードソースの追加管理 UI / 設定化。
  - ETL ジョブのスケジューリング、並列実行制御、詳細な品質チェックルールの実装（quality モジュール拡張）。
  - strategy / execution / monitoring の具象実装（現状は名前空間のみ提供）。

ライセンスやリリース手順（運用メモ）
- 環境変数の必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。これらが未設定の場合 settings のアクセスで ValueError を送出します。".env.example" を参照して .env を作成してください。
- 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。

以上。