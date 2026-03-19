Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

[全文英語版ではなく日本語での説明を含みます。]

Unreleased
---------

(none)

0.1.0 - 2026-03-19
------------------

初回リリース。本リリースでは日本株自動売買プラットフォーム "KabuSys" の基礎的なモジュール群を実装しています。
主な追加点・設計方針、注意点を以下にまとめます。

Added
- パッケージ基盤
  - パッケージエントリポイント src/kabusys/__init__.py を追加し、バージョンを "0.1.0" に設定。公開サブモジュールとして data, strategy, execution, monitoring を宣言。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込みの優先順位: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート・エスケープ、インラインコメントを考慮した堅牢な実装。
  - Settings クラスを提供し、アプリケーションで利用する設定値をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev の便利プロパティ

- Data モジュール（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限を守る _RateLimiter（120 req/min）を実装。
    - リトライ（指数バックオフ、最大3回）、429 の場合は Retry-After ヘッダを優先、408/429/5xx を再試行対象に設定。
    - 401 受信時はリフレッシュトークン経由で ID トークンを自動更新し 1 回だけ再試行する仕組みを実装。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存用の save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE による冪等性）。
    - 型変換ユーティリティ _to_float / _to_int を実装し、入力データの頑健なパースを実現。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead bias のトレースに対応。
  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード取得・パース、記事正規化、DuckDB への保存ワークフローを実装。
    - セキュリティ対策:
      - defusedxml を用いた安全な XML パース（XML Bomb 等に耐性）
      - SSRF 対策: リダイレクト時のスキーム検証、ホストのプライベートアドレス判定（IP/DNS 解決）、_SSRFBlockRedirectHandler を利用した安全なリダイレクト処理
      - 許可スキームは http/https のみ
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - URL の正規化（トラッキングパラメータ除去）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）と RSS pubDate の堅牢なパース。
    - DB 保存関数:
      - save_raw_news: INSERT ... RETURNING id を用いて新規挿入された記事IDのみを返す（チャンク挿入、1 トランザクション）。トランザクション失敗時はロールバック。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への記事-銘柄紐付けをチャンク挿入で実行（ON CONFLICT DO NOTHING、RETURNING による正確な挿入数取得）。
    - 銘柄コード抽出: 4桁数字の候補抽出と known_codes によるフィルタリング（extract_stock_codes）。
    - run_news_collection: 複数 RSS ソースの収集をまとめて実行し、ソース単位で失敗をハンドル（1 ソース失敗でも他は継続）。
    - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを設定。
  - スキーマ（src/kabusys/data/schema.py）
    - DuckDB 向けのテーブル DDL（Raw Layer の raw_prices, raw_financials, raw_news, raw_executions 等の定義）を実装。初期化・管理の基盤となるスキーマ定義を提供。

- Research モジュール（src/kabusys/research）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定基準日の終値から翌日/翌週/翌月等の将来リターンを一括 SQL で計算（horizons は営業日ベース、デフォルト [1,5,21]）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None を返す。ties の取り扱いは平均ランクで実装。
    - rank: 値のランク化（同順位は平均ランク、丸めで ties 検出漏れ対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None を除外）。
    - 実装方針として DuckDB の prices_daily テーブルのみを参照し、本番 API へアクセスしない。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。十分なウィンドウがない場合は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、当日/20日平均出来高比（volume_ratio）を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials の最新（target_date 以前）財務データを用いて PER（EPS が 0/欠損時は None）、ROE を計算。prices_daily と組み合わせて結果を返す。
    - いずれも DuckDB 接続を受け取り prices_daily / raw_financials のみを参照する設計。

- 便利関数の公開（src/kabusys/research/__init__.py）
  - zscore_normalize（kabusys.data.stats から）、calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank をエクスポート。

Security
- ニュース収集での SSRF 対策、defusedxml による安全な XML パース、レスポンスサイズ制限、gzip 解凍後のサイズ検査などを実装。

Performance / Reliability
- J-Quants API クライアントはレート制限（固定間隔スロットリング）とリトライ/バックオフを実装して安定性を確保。
- DB への保存は冪等性を意識した INSERT ... ON CONFLICT / DO UPDATE を利用。
- RSS 保存はチャンク・1 トランザクション単位で行い、INSERT RETURNING により実際に挿入された件数を正確に取得。

Notes / Migration / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - (自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定)
- デフォルト DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
- DuckDB テーブル名（コード中参照）:
  - prices_daily, raw_prices, raw_financials, raw_news, market_calendar, news_symbols 等
- J-Quants API のレート制限は 120 req/min。_RateLimiter により最小間隔を自動調整。
- fetch_* 系はページネーション対応、内部でトークンキャッシュを利用。get_id_token はリフレッシュトークンを用いた処理を行う。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Security
- ニュースフィード処理での SSRF/XML 脆弱性対策を導入（詳細は上記 Security セクション参照）。

開発者向けメモ
- 単体テストを行う際は自動 .env ロードを無効にすることで環境の隔離が可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- ネットワーク呼び出し部分（jquants_client._request, news_collector._urlopen 等）はモックしてテスト可能なように設計されています。
- DuckDB 接続は duckdb.DuckDBPyConnection を受け取るインタフェースになっています。

（補足）この CHANGELOG はソースコード注釈と設計コメントから推測して作成しています。実際のリリースノート作成時は追加の変更点や後発の修正を適宜反映してください。