# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」の仕様に準拠しています。

最新リリース: 0.1.0

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-18

Added
- パッケージ基本情報
  - パッケージ初期バージョンを導入: `kabusys.__version__ = "0.1.0"`。
  - パッケージ公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` で定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途など）。
  - .env のパースロジックを強化:
    - 空行/コメント、`export KEY=val` 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理に対応。
  - 環境変数読み込み時の上書き制御（override）と保護（protected）を実装。
  - 必須環境変数取得ユーティリティ `_require()` と Settings クラスを提供。
    - J-Quants / kabu API / Slack / DB パス等のプロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。
  - Settings に is_live / is_paper / is_dev のヘルパーを追加。

- Data レイヤー（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）を追加:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 429 の Retry-After ヘッダを優先。
    - 401 発生時はリフレッシュトークンで自動的に ID トークンを取得して 1 回リトライ（無限再帰防止）。
    - ページネーション対応のデータ取得関数を提供:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存ユーティリティ（冪等性を確保するため ON CONFLICT を使用）:
      - save_daily_quotes -> raw_prices テーブル
      - save_financial_statements -> raw_financials テーブル
      - save_market_calendar -> market_calendar テーブル
    - レスポンス／CSV値変換ユーティリティ `_to_float`, `_to_int` を提供（不正値処理を厳密に実施）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias のトレースを可能に。

  - ニュース収集モジュール（kabusys.data.news_collector）を追加:
    - RSS フィード取得と前処理、DuckDB への冪等保存ワークフローを実装。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML Bomb などの対策）。
      - SSRF 対策（URL スキーム検証、リダイレクト先のスキーム/ホスト検証、プライベート IP 判定）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
      - 許可スキーム: http/https のみ。
    - URL 正規化（トラッキングパラメータの除去、クエリソート、フラグメント削除）と記事 ID 生成（正規化 URL の SHA-256 の先頭32文字）。
    - テキスト前処理（URL 除去・空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を使い、実際に挿入された記事IDのみを返却。チャンク＆トランザクション処理。
      - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けを冪等に保存（INSERT ... RETURNING を使用）。
    - 銘柄コード抽出ユーティリティ extract_stock_codes（テキスト中の 4 桁数字を known_codes でフィルタ、重複除去）。
    - run_news_collection: 複数ソースを巡回して収集・保存・銘柄紐付けを一括実行（ソース単位でのエラーハンドリング）。

  - DuckDB スキーマ定義（kabusys.data.schema）を追加:
    - Raw Layer の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義）。
    - 各テーブルに適切な型チェック制約と主キーを設定。
    - スキーマ初期化のための基盤を提供。

- Research レイヤー（kabusys.research）
  - feature_exploration モジュールを追加:
    - calc_forward_returns: DuckDB の prices_daily を使って複数ホライズン（デフォルト 1,5,21）にわたる将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンを code で結合し、スピアマンのランク相関（IC）を計算（ties の扱い、無効値の除外、サンプル不足時は None）。
    - rank: 同順位は平均ランクを割り当てるランク化ユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を標準ライブラリのみで算出（None 値除外）。
    - research パッケージ __all__ へ各ユーティリティを公開。
    - Research 実装方針: DuckDB の prices_daily/table のみ参照し、本番発注 API へはアクセスしない設計（安全性）。

  - factor_research モジュールを追加:
    - calc_momentum:
      - mom_1m / mom_3m / mom_6m（連続営業日をベースに LAG を利用して算出）。
      - ma200_dev（200 日移動平均乖離率、ウィンドウに 200 行未満なら None）。
      - スキャン範囲にバッファを与えて週末/祝日を吸収。
    - calc_volatility:
      - atr_20（20 日 ATR の単純平均、データ欠損時は None）、atr_pct（ATR / close）、avg_turnover、volume_ratio を計算。
      - true_range を NULL 伝播を考慮して算出し、カウントで完全なウィンドウを判定。
    - calc_value:
      - raw_financials から target_date 以前の最新財務データを銘柄ごとに取得し、per（close / eps：eps=0/NULL は None）と roe を算出。
      - DuckDB のウィンドウ関数（ROW_NUMBER）を使用して最新レコードを選択。
    - 研究用ファクター群（Momentum/Value/Volatility/Liquidity）を DuckDB SQL と Python で実装。外部 API 呼び出しは行わない。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / 注意事項
- research モジュール群は標準ライブラリ・DuckDB のみを想定しており、本番の注文/発注 APIへは一切アクセスしない設計です。
- J-Quants クライアントは自動でトークンを取得・リフレッシュします。JQUANTS_REFRESH_TOKEN を必須環境変数として設定してください。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して制御可能です。
- DuckDB への保存処理は ON CONFLICT を用いて冪等に動作するように実装していますが、スキーマやテーブル名の変更は互換性に影響します。既存 DB を使う際はご注意ください。

作者: KabuSys（コードベースから推測して記載）
