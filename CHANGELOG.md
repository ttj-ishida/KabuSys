Changelog
=========

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトのバージョン付けは SemVer を使用します。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-19
--------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基盤実装を追加。
- パッケージ構成:
  - kabusys: パッケージエントリポイント（__version__ = 0.1.0、__all__ 指定）。
  - サブパッケージのプレースホルダ: execution, strategy（将来の実装用名前空間を確保）。

- 設定・環境管理 (kabusys.config):
  - .env ファイルと OS 環境変数の自動読み込み機能を実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env /.env.local の優先度制御（OS 環境変数を保護する protected 機構）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等）。
  - 入力検証: KABUSYS_ENV・LOG_LEVEL の許可値検査、必須環境変数未設定時の明確なエラー。

- データ取得・保存ユーティリティ (kabusys.data.jquants_client):
  - J-Quants API クライアントを実装。
    - rate limiting（120 req/min、固定間隔スロットリング）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx を対象。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を使用して重複を排除。
    - データ型変換ユーティリティ (_to_float, _to_int)。

- ニュース収集 (kabusys.data.news_collector):
  - RSS フィードから記事を収集して raw_news / news_symbols へ冪等保存する完全なパイプラインを実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を使った XML パース（XML Bomb 等への耐性）。
    - SSRF 対策: URL スキーム検証、リダイレクト時のスキーム/ホスト検査、プライベート IP 判定で内部アドレスへの到達を防止。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査（Gzip-bomb 対策）。
    - 受信時の Content-Length 検査と実際の読み取り上限。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字により生成して冪等性を保証（utm_* 等のトラッキングパラメータを除去）。
  - 実装上の利便性・性能:
    - 前処理: URL 除去・空白正規化（preprocess_text）。
    - 銘柄コード抽出（4桁数字、known_codes フィルタ）。
    - DB への一括 INSERT はチャンク化（_INSERT_CHUNK_SIZE）してトランザクションでまとめる。INSERT ... RETURNING で実際に挿入された件数を返す。
    - run_news_collection により複数ソースを逐次処理。ソース単位でエラーハンドリング。

- DuckDB スキーマ (kabusys.data.schema):
  - DataSchema.md に基づく初期のテーブル定義を追加（Raw Layer を中心に定義）。
    - raw_prices, raw_financials, raw_news, raw_executions などの DDL を含む（NOT NULL / CHECK / PRIMARY KEY 等の制約を定義）。
  - スキーマ初期化用モジュールの基礎を提供。

- リサーチ (kabusys.research):
  - 研究・特徴量探索用 API を提供。
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily から一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ不足（<3 レコード）時は None。
    - factor_summary: 各カラムに対する count/mean/std/min/max/median 集計（None を除外）。
    - rank: 同順位は平均ランクで処理し、丸め誤差対策の round(..., 12) を使用。
    - 設計方針として標準ライブラリのみを使用（pandas 等に依存しない）。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算（価格履歴をウィンドウ指定して DuckDB 上で算出）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true range の NULL 伝播を適切に扱う）。
    - calc_value: raw_financials から最新財務（target_date以前）を拾い、PER/ROE を計算（EPS が 0 または欠損なら None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番発注 API へはアクセスしない設計。
  - research パッケージの __all__ に主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。（zscore_normalize は kabusys.data.stats から提供される想定）

Changed
- （初版）ライブラリ設計の基本方針と API を確定。
  - Look-ahead Bias 対策（fetched_at を UTC で記録する設計）や冪等化方針を明示。
  - DuckDB を中心としたデータレイヤー設計を採用。

Fixed
- N/A（初回リリース）。

Security
- news_collector に複数の SSRF 対策を導入（スキーム検証、リダイレクト検査、プライベートIP判定）。
- XML パースに defusedxml を使用して安全性を確保。
- ネットワーク呼び出しのタイムアウトやレスポンスサイズチェックを追加。

Performance
- J-Quants クライアントでレートリミッタを導入し、API レート制限を厳守。
- News 保存処理でチャンク化バルク INSERT を使い、トランザクションをまとめてオーバーヘッドを低減。
- DuckDB 側のウィンドウ関数を活用して特徴量計算を SQL で効率的に実行。

Notes for users
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須チェックされます。
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの .env および .env.local を自動読み込みします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / defusedxml などの依存ライブラリが必要です。research の一部ユーティリティは kabusys.data.stats に依存します（zscore_normalize を参照）。
- 本リリースでは Execution / Strategy の発注ロジックは未実装（パッケージ名前空間は用意済み）。発注周りの実装は今後のリリースで追加予定。

Acknowledgements / Design decisions
- データの「いつ知り得たか」を追跡するため fetched_at を UTC で記録する設計にしています（Look-ahead Bias を防止するため）。
- 冪等性を重視し、外部データの DB 保存は基本的に ON CONFLICT による上書き/スキップで実装しています。
- 研究系処理は外部 API に依存しない（DuckDB のみ参照）方針で、安全にオフラインで検証できるようにしています。