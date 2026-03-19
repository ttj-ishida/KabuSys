# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、このプロジェクトの初期リリースとして以下をまとめています。

## [Unreleased]

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース (kabusys 0.1.0) を追加。
- パッケージエントリポイント
  - src/kabusys/__init__.py にてバージョン管理と公開 API を定義（data, strategy, execution, monitoring）。
- 環境設定/読み込み
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - export プレフィックス対応、クォート付き/なしの値パース、インラインコメント処理を含む堅牢な .env パーサを実装。
    - OS 環境変数保護（既存環境変数はデフォルトで上書きしない）、`.env.local` は上書き用にサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 必須キー取得ヘルパー `_require` と Settings クラス（J-Quants トークン、kabu API、Slack、DBパス、環境モード、ログレベル等をプロパティとして提供）。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値チェック）。
- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API から日次株価、財務データ、マーケットカレンダーを取得するクライアントを実装。
    - API レート制限管理（120 req/min 固定間隔スロットリング）を内部 RateLimiter で実装。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
    - 401 応答時は自動でリフレッシュトークンから ID トークンを取得して 1 回リトライ（無限再帰対策あり）。
    - ページネーション対応（pagination_key の扱い）およびモジュール内トークンキャッシュを実装。
    - DuckDB に対する保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等化を行う。
    - 型変換ユーティリティ `_to_float`, `_to_int` を提供（不正値/空値の安全な扱い）。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を収集し DuckDB の raw_news / news_symbols へ保存する機能を実装。
    - セキュリティ対策: defusedxml による XML パース、防止済みリダイレクトハンドラで SSRF を軽減、ホストのプライベートアドレス検査、許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）を実装。
    - URL 正規化（トラッキングパラメータ削除、フラグメント除去、クエリソート）と記事 ID 生成（正規化 URL の SHA-256 先頭32文字）による冪等性確保。
    - テキスト前処理（URL 除去、空白正規化）、記事IDベースのバルク INSERT（チャンク化、トランザクション、INSERT ... RETURNING）を実装。
    - 銘柄コード抽出（4桁数字パターン、known_codes によるフィルタリング）と一括紐付け保存ロジックを提供。
    - run_news_collection により複数ソースを個別エラーハンドリングで収集・保存する統合ジョブを実装。
- DuckDB スキーマ定義/初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の層を想定したスキーマ定義の雛形と DDL を実装（raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義を含む）。
    - 各テーブルに主キー制約・型チェックを付与（例: price/volume の非負チェック）。
- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - StrategyModel に基づく定量ファクター計算を提供（prices_daily / raw_financials を参照）。
    - モメンタム: calc_momentum（mom_1m、mom_3m、mom_6m、ma200_dev）を実装。200日移動平均の件数判定などデータ不足時の None 処理あり。
    - ボラティリティ/流動性: calc_volatility（20日 ATR、相対ATR、20日平均売買代金、出来高比）を実装。true_range の NULL 伝播制御等を考慮。
    - バリュー: calc_value（最新財務データの取得と PER / ROE 算出）を実装。raw_financials から target_date 以前の最新レコードを取得。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズンのリターンを一度のクエリで取得）。
    - IC（Information Coefficient）計算: calc_ic（スピアマン順位相関）と rank（同順位は平均ランク、round による ties 対応）。
    - ファクター統計要約: factor_summary（count/mean/std/min/max/median）を実装。
  - src/kabusys/research/__init__.py に主要ユーティリティを集約してエクスポート。
- データ処理ユーティリティ（参照）
  - research モジュールは外部ライブラリに依存せず標準ライブラリ＋DuckDB を利用する設計を明記。
- その他
  - 主要モジュールでのロギングを実装（logger を利用した情報/警告/例外ログ）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- RSS 収集での SSRF 対策、defusedxml による安全な XML パース、レスポンスサイズ制限、gzip 解凍後の検査を実装。
- J-Quants クライアントはトークン管理とリフレッシュの仕組みを組み込み、無限リフレッシュや誤用を避ける安全対策を施している。

### Notes / Design decisions
- DuckDB をデータレイク層として使用し、ほとんどのデータ処理は SQL ウィンドウ関数と Python の組合せで実装。これによりデータ量に対して効率的な集計が可能。
- 外部 HTTPリクエストは再試行・バックオフ・レートリミットで堅牢化。ページネーションは pagination_key により処理。
- db への保存は可能な限り冪等化（ON CONFLICT）し、重複や再実行に耐える構成。
- research モジュールは本番口座や発注 API にはアクセスしない設計。

------------

今後のリリースでは以下を予定しています（例）:
- strategy / execution 層の具体的な実装（発注ロジック、kabu ステーション API 連携）
- モニタリング / Slack 通知の統合
- テストカバレッジと CI/CD の整備

--- 

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴と差異がある場合は適宜修正してください。）