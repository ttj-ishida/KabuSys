CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

0.1.0 - 2026-03-18
------------------

Initial release.

Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開用のトップレベル __all__ を定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロードを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して判定（CWD 非依存）。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装（export KEY=val, クォート、インラインコメント対応）。
  - 環境値取得ユーティリティ Settings を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得。
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb） / SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 検証（development / paper_trading / live）とロギングレベル検証（DEBUG/INFO/...）。
    - is_live / is_paper / is_dev の bool ヘルパー。

- データ取得・保存 (kabusys.data)
  - J-Quants API クライアント (jquants_client)
    - HTTP クライアント実装（urllib ベース）。
    - レート制限（120 req/min）を固定間隔スロットリングで守る RateLimiter 実装。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス/エラーを判定して再試行。
    - 401 Unauthorized を検出した場合はリフレッシュトークンから自動で id_token を取得して 1 回リトライ。
    - ページネーション対応を実装（pagination_key を利用）。
    - データを DuckDB に冪等に保存する関数:
      - save_daily_quotes -> raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
      - save_financial_statements -> raw_financials テーブルへ INSERT ... ON CONFLICT DO UPDATE
      - save_market_calendar -> market_calendar テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - 型変換ユーティリティ _to_float / _to_int（不正値や空文字列を安全に None にする）。
    - fetched_at を UTC ISO8601 形式で記録（Look-ahead bias の抑止、取得時刻のトレース可能性）。

  - ニュース収集モジュール (news_collector)
    - RSS フィードからの記事収集・正規化・DB 保存パイプラインを実装。
    - セキュリティ対策:
      - defusedxml を使用して XML 関連攻撃（XML Bomb 等）に対処。
      - SSRF 対策: リダイレクト先および最終 URL のスキーム検証、プライベートアドレス判定（IP/ホストの DNS 解決）を実施。リダイレクト専用ハンドラ実装。
      - 受信サイズ上限設定（MAX_RESPONSE_BYTES = 10MB）と超過検出（Content-Length および読み込みバイト数）。
      - gzip 解凍後のサイズ再検査（Gzip bomb 対策）。
      - URL 正規化とトラッキングパラメータ除去（utm_* 等）により同一記事判定を安定化。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - DB 保存の挙動:
      - save_raw_news はチャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのみを返す。
      - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付け（news_symbols）を一括保存。トランザクションで安全に処理。
    - テキスト前処理ユーティリティ（URL 除去・空白正規化）と RFC2822 pubDate パース（失敗時は warning を出して現在時刻で代替）。
    - 銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタリング）を実装。
    - デフォルト RSS ソースに Yahoo Finance のカテゴリ RSS を追加。

- DuckDB スキーマ (kabusys.data.schema)
  - Raw 層の DDL 定義を追加（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含むスキーマモジュールを実装）。
  - 各テーブルに主キー、型、簡易 CHECK 制約を付与し、データ整合性を担保。

- 研究・特徴量 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns(conn, target_date, horizons=None)
      - prices_daily テーブルを参照し、指定日の終値から指定ホライズン（既定 [1,5,21]）の将来リターンを一括取得。
      - ホライズン上限チェック（1..252）。
      - 結果は [{date, code, fwd_1d, fwd_5d, ...}, ...] のリスト。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足(有効レコード<3)の場合は None を返す。
      - 内部に rank() ユーティリティを備え、同順位は平均ランクを使用。丸め（round(v, 12)）で浮動小数の ties 検出漏れを低減。
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を計算（None と非数値は除外）。
    - 標準ライブラリのみで実装（pandas 等に依存しない）という設計方針。
  - factor_research モジュール:
    - calc_momentum(conn, target_date)
      - mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。必要データ不足時は None を返す。
      - DuckDB のウィンドウ関数を用いた効率的な一括計算。
    - calc_volatility(conn, target_date)
      - atr_20（20日 ATR 平均）、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を適切に制御。
    - calc_value(conn, target_date)
      - raw_financials から target_date 以前の最新財務データを取得して per / roe を計算（EPS が 0 または NULL の場合は per を None に）。
    - 定数として窓長やスキャン範囲のバッファ（カレンダー日数）を明記し、週末/祝日を吸収する方針を採用。

- モジュールエクスポート (kabusys.research.__init__)
  - 主要ユーティリティを再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Notes / 使用上の注意
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須取得され、未設定時は ValueError を送出します。
- 自動 .env ロード
  - パッケージ初期化時にプロジェクトルートが見つかれば .env/.env.local を自動で読み込みます。テストや環境設定でこれを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB テーブル
  - スキーマモジュールで定義されるテーブルを事前に作成しておくことが想定されています（raw_prices, raw_financials, raw_news, market_calendar, raw_executions など）。
- 研究モジュールの設計制約
  - research パッケージは外部ライブラリに依存しない実装（標準ライブラリ + duckdb）を意図しています。大量データ処理の際はクエリ側で最適化を行うことを推奨します。
- jquants_client の挙動
  - API 呼び出しは固定レートでスロットリングされ、リトライやトークン自動更新の挙動が入ります。テストでは _get_cached_token/_rate_limiter 等をモック可能です。
- news_collector の安全性
  - RSS フィード取得はリダイレクトごとの検査、受信サイズ上限、gzip 解凍後の検査、XML パースの例外処理を備えており、過度なリソース消費や内部ネットワークへのアクセスを抑止します。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

既知の制限 / TODO
- strategy および execution パッケージは __init__.py のみで実装は最小限（将来的な戦略・発注ロジックの追加予定）。
- zscore_normalize は kabusys.data.stats に依存しており、data パッケージ側に実装が必要（現状リストで再エクスポート）。
- 一部の SQL は DuckDB のウィンドウ関数に依存するため、巨大テーブルでの実行時はメモリ/パフォーマンス評価が必要。

Contact
- バグ報告・改善提案はリポジトリの Issue にお願いします。