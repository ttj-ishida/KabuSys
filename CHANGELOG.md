CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に従います。
セマンティックバージョニングを採用しています。

Unreleased
----------

（現在の作業中の変更はここに記載します。現時点ではなし。）

0.1.0 - 2026-03-18
------------------

初回公開リリース。日本株自動売買システムの基礎モジュール群を導入しました。
主な追加点・設計方針・注意点は以下の通りです。

Added
- パッケージ初期化
  - kabusys.__init__ を追加（バージョン: 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring（strategy/execution はパッケージのみ用意）。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、インラインコメント（一定条件）を考慮した堅牢な実装。
  - Settings クラスにアプリケーション設定を集約（J-Quants トークン、kabu API 設定、Slack、DBパス、環境モード、ログレベルなど）。
  - 環境値のバリデーション（KABUSYS_ENV の有効値検査、LOG_LEVEL の検査）を実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（内部 RateLimiter）。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 時は Retry-After を優先。
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
  - ページネーション対応で全件取得。
  - DuckDB へ保存する冪等的な保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。ON CONFLICT DO UPDATE/DO NOTHING を利用。
  - 型変換ユーティリティ（_to_float/_to_int）を実装し不正な値を安全に扱う。
  - fetched_at を UTC で記録し Look‑ahead bias のトレースを可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得して raw_news / news_symbols に保存する機能を実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録。
  - セキュリティと堅牢性:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時のスキーム検証・プライベートアドレス拒否、ホスト事前チェック。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を設け、読み込み・gzip 解凍後にもチェック。
    - トラッキングパラメータの削除・URL 正規化（記事 ID は正規化 URL の SHA-256 先頭32文字）。
  - テキスト前処理（URL 除去・空白正規化）と記事ID生成を実装。
  - 銘柄コード抽出（4桁数字、known_codes フィルタ）と銘柄紐付け機能。
  - DB への保存はチャンク化・トランザクションで行い、INSERT ... RETURNING を用いて実際に挿入された件数/ID を返す。

- データスキーマ（kabusys.data.schema）
  - DuckDB 向けの初期スキーマ定義（Raw Layer の DDL）を追加。
  - raw_prices / raw_financials / raw_news / raw_executions 等のテーブル定義を含む（チェック制約・PK を指定）。

- リサーチ（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを一括取得する関数。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算する関数。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティ。
  - factor_research:
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離の計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の計算。
    - calc_value: PER（株価 / EPS）、ROE の計算（raw_financials と prices_daily を結合）。
  - 設計方針: DuckDB 接続を受け取り prices_daily / raw_financials のみ参照。外部 API 呼び出しは行わない。外部ライブラリを使わず標準ライブラリと SQL で実装。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- DB 保存時に主キー欠損行をスキップし警告ログを残すようにして不正データによる障害を回避（jquants_client.save_*、news_collector.save_raw_news 等）。

Security
- RSS 取得処理における SSRF 対策を強化（リダイレクト検証、プライベートアドレス拒否、スキームチェック）。
- XML パースに defusedxml を採用。
- ネットワーク入力のサイズ検査・gzip 解凍後のサイズ検査を導入して DoS 対策。

Performance / Implementation notes
- リサーチの各集計は DuckDB のウィンドウ関数を活用して一度のクエリで複数指標を効率的に取得。
- calc_forward_returns / calc_momentum / calc_volatility はスキャン範囲をホライズンに基づくカレンダーバッファで限定し、不要な全件走査を避ける設計。
- news_collector は INSERT をチャンク化して SQL 長・パラメータ数の上限を回避。

Known limitations / Notes
- research モジュールは外部ライブラリ（pandas など）に依存しないため、極端に大きなデータセットでの処理は検索・集計の観点で制約がある可能性があります。
- calc_value は EPS が 0 / NULL の場合に PER を None とする（除算回避）。
- J-Quants API を利用するには環境変数 JQUANTS_REFRESH_TOKEN が必須。その他 Slack / Kabu API 等も Settings で必須チェックあり。
- スキーマ定義は Raw Layer を中心に実装済み。Processed / Feature / Execution 層の追加定義は今後のリリースで拡張予定。

開発者向け備考
- 自動 .env ロードが不要/邪魔なテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector._urlopen はテスト用にモック差し替え可能な設計になっています。
- jquants_client 内のトークンキャッシュはモジュールレベルで保持され、ページネーション間で共有されます。必要に応じて _get_cached_token(force_refresh=True) を利用して更新可能です。

将来の予定（例）
- Processed / Feature / Execution 層のスキーマとデータパイプラインの追加。
- Strategy/Execution モジュール内でのバックテスト・実取引連携の実装。
- News の自然言語処理（語種判別、エンティティ抽出）や記事のクラスタリング機能の追加。

--- 

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして利用する際は、必要に応じて文言・日付・カテゴリを調整してください。）