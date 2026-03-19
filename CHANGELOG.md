Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコードから推測できる「注目すべき変更点」を初期リリース 0.1.0 としてまとめています。

CHANGELOG.md
=============
すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に従います。  

Unreleased
----------
（現在なし）

[0.1.0] - 2026-03-19
-------------------
初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

Added
- パッケージの公開エントリポイントを追加
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサ実装（export 形式、クォート、インラインコメント処理、エスケープ対応）
  - Settings クラスを提供し、主要な設定をプロパティ経由で取得
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV 検証（development/paper_trading/live の限定）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ユーティリティ

- データ取得・保存ロジック (kabusys.data.jquants_client)
  - J-Quants API クライアント実装
    - 固定間隔スロットリングによるレート制限（120 req/min, _RateLimiter）
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ
    - ページネーション対応（pagination_key）
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead bias を回避
  - 主な API 関数:
    - get_id_token(refresh_token: str | None) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB への冪等保存関数:
    - save_daily_quotes(conn, records) — raw_prices へ ON CONFLICT DO UPDATE
    - save_financial_statements(conn, records) — raw_financials へ ON CONFLICT DO UPDATE
    - save_market_calendar(conn, records) — market_calendar へ ON CONFLICT DO UPDATE
  - 型安全な変換ユーティリティ: _to_float, _to_int（不正入力や空値は None）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集と前処理の実装
    - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
    - テキスト前処理（URL 除去・空白正規化）
    - XML パースに defusedxml を使用（XML-Bomb 等の防御）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクトハンドラでリダイレクト先のスキームとプライベートアドレス検査
      - 初回 URL のホストもプライベートアドレスでないことを確認
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック
    - RSS 取得: fetch_rss(url, source, timeout)
  - DB 保存:
    - save_raw_news(conn, articles) — チャンク INSERT、ON CONFLICT DO NOTHING、INSERT ... RETURNING で実際に挿入された記事IDを返す
    - save_news_symbols / _save_news_symbols_bulk — news_symbols テーブルへの銘柄紐付けをチャンク挿入で処理
  - 銘柄コード抽出:
    - extract_stock_codes(text, known_codes) — 4桁数字パターンを抽出し、known_codes と照合して重複除去

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw Layer のテーブル定義（DDL）
    - raw_prices（PK: date, code）
    - raw_financials（PK: code, report_date, period_type）
    - raw_news（PK: id）
    - raw_executions（定義途中まで含む）
  - 初期化ユーティリティ（DDL の CREATE TABLE IF NOT EXISTS を含む）

- リサーチ（ファクター計算）モジュール (kabusys.research)
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None) — 翌日/翌週/翌月等の将来リターンを DuckDB の prices_daily テーブルから一括取得して計算
    - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関（IC）を計算
    - factor_summary(records, columns) — count/mean/std/min/max/median を計算
    - rank(values) — 同順位は平均ランクにするランク関数（丸め誤差対策で round）
    - 設計方針: 標準ライブラリのみで実装（pandas 等に非依存）、本番 API 呼び出しなし
  - factor_research.py:
    - calc_momentum(conn, target_date) — mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離率）
    - calc_volatility(conn, target_date) — atr_20, atr_pct, avg_turnover, volume_ratio（20日ウィンドウ）
    - calc_value(conn, target_date) — per (price/EPS), roe（raw_financials から最新報告を取得）
    - 各関数は prices_daily / raw_financials のみ参照し、本番発注にはアクセスしないことを明記

- パッケージ再エクスポート (kabusys.research.__init__)
  - calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank を公開

Security
- RSS パーサに defusedxml を採用し XML 関連攻撃を軽減
- ニュース収集で SSRF 対策を実装（スキーム検証、プライベートホスト拒否、リダイレクト時チェック）
- .env 自動読み込みで OS 環境変数を保護（.env.local は上書き可能だが、既存の OS 環境変数は保護される）

Performance & Reliability
- J-Quants クライアントで固定間隔レートリミッタを導入（API レート制限遵守）
- HTTP 再試行（指数バックオフ）を実装し一時的なエラー耐性を向上
- DuckDB へのバルク INSERT はチャンク化してトランザクションで処理、INSERT ... RETURNING を使用して実際の挿入結果を取得
- News symbols 紐付けは重複除去・チャンク挿入で効率化

Notes / Usage tips
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db
- KABUSYS_ENV の値は development / paper_trading / live のいずれかにする必要がある
- research モジュールは外部ライブラリに依存しない実装（pandas 非依存）で、DuckDB の prices_daily / raw_financials テーブルを参照する

Known issues / Limitations
- 一部テーブル定義（raw_executions の DDL）がファイル内で途中までしか示されておらず、Execution Layer の完全なスキーマは未完（今後の追加予定）
- factor_research の一部ファクター（PBR、配当利回りなど）は未実装で将来追加の余地あり
- jquants_client の _RETRY_STATUS_CODES は現在 {408, 429} を含むが、必要に応じて拡張可能

Acknowledgments
- 本リリースはコードベースから推測してまとめた初期ドキュメントです。実際の運用にあたっては README や DataSchema.md / DataPlatform.md / StrategyModel.md 等の設計文書を参照してください。

------------------------------------------------------------------------------
この CHANGELOG はリポジトリ内のコード（src/kabusys/ 以下）から明示・暗示される機能や設計方針をもとに作成しました。記載内容に誤りや補足が必要な点があれば教えてください。