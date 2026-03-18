CHANGELOG
=========

全般的な注意
------------
この CHANGELOG はパッケージのコードベースから推測して作成したものです。実際のコミット履歴が存在する場合はそちらを優先してください。

フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------
（現在の作業ブランチに対する未リリースの変更はここに記載します。現状は無し。）

[0.1.0] - 2026-03-18
--------------------

Added
- 初回公開リリース (v0.1.0)
  - パッケージエントリポイント:
    - src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュールリスト __all__ を追加。
  - 設定管理:
    - src/kabusys/config.py
      - .env ファイルおよび環境変数から設定を読み込む自動ロード実装（プロジェクトルートを .git または pyproject.toml で探索）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - .env パーサ実装（コメント、export 形式、クォートとエスケープ、インラインコメントルール対応）。
      - 必須環境変数取得用の Settings クラスを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティ、DUCKDB_PATH/SQLITE_PATH のデフォルトパス、KABUSYS_ENV と LOG_LEVEL の検証）。
  - Data 層（DuckDB）:
    - src/kabusys/data/schema.py に Raw/Processed/Feature/Execution 層のスキーマ定義（raw_prices, raw_financials, raw_news 等の DDL）を追加（初期化用モジュール）。
  - J-Quants API クライアント:
    - src/kabusys/data/jquants_client.py
      - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
      - リトライロジック（指数バックオフ、最大3回、特定ステータスでの再試行）を実装。
      - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組み。
      - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
      - 型変換ユーティリティ _to_float/_to_int、id_token キャッシュ管理。
  - ニュース収集:
    - src/kabusys/data/news_collector.py
      - RSS フィード取得と記事保存処理（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
      - セキュリティ対策: defusedxml による XML パース、SSRF 対策（リダイレクト時のスキーム/ホスト検査、プライベートアドレス拒否）、許可スキームを http/https に限定。
      - 大容量レスポンス対策: MAX_RESPONSE_BYTES（10 MB）を超えるレスポンスを拒否、gzip 対応と解凍後サイズ検証（Gzip bomb 対策）。
      - URL 正規化（トラッキングパラメータ除去、クエリソート）、記事ID を SHA-256 の先頭 32 文字で生成して冪等性を担保。
      - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4 桁数字、既知コードセットでフィルタ）。
      - DB 挿入はチャンク分割とトランザクションで効率的かつ安全に実行（INSERT ... RETURNING を使用して実際に挿入された件数を取得）。
  - Research / Feature 計算:
    - src/kabusys/research/factor_research.py
      - Momentum, Volatility, Value (一部) の定量ファクターを計算する関数を実装:
        - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 欠損時は None）。
        - calc_volatility: atr_20（ATR）、atr_pct（ATR/close）、avg_turnover、volume_ratio（20 日移動平均を用いる）。
        - calc_value: raw_financials から最新の財務を取得して PER（EPS なし/0 の場合 None）、ROE を算出。
      - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計（実際の発注・外部 API にはアクセスしない）。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 任意ホライズン（デフォルト 1/5/21 営業日）で将来リターンを計算。1 クエリでまとめて取得する最適化あり。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。データ不足や定数分散時の None 返却に対応。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
      - rank: タイ（同順位）に対して平均ランクを付与するランク関数（浮動小数の丸めで ties 検出を安定化）。
    - src/kabusys/research/__init__.py で主要関数を再エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank と zscore_normalize の参照）。
  - その他ユーティリティ:
    - 各モジュールでの詳細なログ出力（logger）と入力検証（引数型や範囲チェック）を充実させ、エラー時は適切に例外や警告を発行。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集モジュールにおける複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策: 最終 URL のスキーム/ホスト検証、リダイレクトハンドラでの事前検査、プライベート IP/ホストの拒否。
  - レスポンスサイズ上限チェック、gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - URL スキーム検証により file:, javascript:, mailto: 等を拒否。

注記（利用者・開発者向け）
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティで _require によりチェック）。
  - 任意/デフォルト: KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL、DUCKDB_PATH, SQLITE_PATH。
  - 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB スキーマ:
  - raw_* 系テーブルを中心に DDL を定義。初期化処理（スキーマ作成関数）は schema モジュールに用意されています（DDL の内容を参照してください）。
- J-Quants クライアント:
  - API の呼び出しが 401 を受けた場合、自動でリフレッシュを試みます（1 回のみ）。無限再帰を防ぐため内部呼び出しでは allow_refresh=False を使っています。
  - レート制限、リトライ挙動（対象ステータス、Retry-After の考慮）を実装済み。
- NewsCollector:
  - run_news_collection は sources 毎に独立してエラーハンドリングを行うため、あるソースの失敗が全体を停止させません。
  - 銘柄コード抽出は 4 桁数字かつ known_codes に含まれるもののみを採用します。known_codes を渡さない場合は紐付けをスキップします。

将来の改善候補（推奨）
- テスト: ネットワーク周り（_urlopen、_request）や DuckDB 保存処理をモックした単体テストを追加して安全性を高める。
- CLI / ジョブスケジューラ: ニュース収集やデータ取得ジョブを cron などから起動するための CLI 層、あるいはスケジューラー統合。
- Feature 層・戦略実行: Feature layer の永続化、strategy/execution モジュールの具体実装（現在はパッケージプレースホルダ）。
- metrics / observability: API 呼び出し数・レートリミット、DB 挿入数などを可視化するメトリクス導入。

付記
- 本 CHANGELOG はコードの内容から機能・意図を推測して作成しています。実際のリリースノートとして利用する際は、コミットログやリリース管理情報での確認を推奨します。