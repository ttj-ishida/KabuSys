CHANGELOG
=========
（Keep a Changelog 準拠）
このファイルでは kabusys のリリースごとの重要な変更点を記録します。

フォーマット
- 変更はカテゴリ（Added, Changed, Fixed, Security, Deprecated, Removed）ごとに整理します。
- 初期リリースでは主な追加機能と設計上の注意点を列挙しています。

Unreleased
----------
（現在の開発中の変更はここに記載）

[0.1.0] - 2026-03-18
-------------------
Added
- パッケージ初期リリース: 基本モジュールを実装。
  - kabusys.__init__.py
    - __version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml ベース）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント扱い（# の前がスペース/タブの場合）
  - 環境変数読み込みの上書き制御（override / protected）を実装し、OS 環境変数の保護に対応。
  - Settings クラスにプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH の既定値と Path 変換
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便宜プロパティ
- データ取得・保存ライブラリ (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限: 固定間隔スロットリング（120 req/min を想定、_RateLimiter）。
  - リトライロジック: 指数バックオフ、最大3回、ステータスコード 408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時の自動トークンリフレッシュ（1 回）と ID トークンのモジュールキャッシュ化（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE / DO NOTHING）:
    - save_daily_quotes -> raw_prices（fetched_at を UTC で記録）
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - データ型変換ユーティリティ:
    - _to_float: 空/変換失敗は None
    - _to_int: "1.0" は許容して int に、非整数の小数文字列は None（意図しない切り捨て防止）
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードの取得・前処理・DuckDB への保存ワークフローを実装。
  - セキュリティ / 安全性対策:
    - defusedxml による XML パース（XML Bomb 等の緩和）
    - リダイレクト検査を含む SSRF 対策（_SSRFBlockRedirectHandler）
    - ホストがプライベートアドレスかを判定して拒否（DNS 解決結果も検査）
    - URL スキーム検証（http/https のみ許可）
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES=10MB、gzip 解凍後も検証）
    - User-Agent, Accept-Encoding ヘッダ制御、タイムアウト対応
  - 記事 ID 生成: 正規化 URL の SHA-256（先頭32文字）を使用し冪等性を保証。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリソートを実施。
  - テキスト前処理: URL 除去・空白正規化（preprocess_text）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、新規挿入された記事 ID のリストを返す。チャンク化（_INSERT_CHUNK_SIZE）して 1 トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク・トランザクションで保存（ON CONFLICT DO NOTHING、INSERT ... RETURNING で正確な挿入数を取得）。
  - 銘柄抽出:
    - 4 桁数字パターンで候補を抽出し、known_codes に含まれるもののみ返す（重複除去）。
  - デフォルト RSS ソースに Yahoo Finance Business RSS を含む。
- Research（特徴量・ファクター計算） (kabusys.research)
  - feature_exploration.py:
    - calc_forward_returns: 指定日から N 営業日先のリターンを一度に取得（DuckDB の LEAD を利用）。horizons の検証（1〜252）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（Spearman ρ）を計算。レコード不足や分散ゼロは None を返す。
    - rank: 同順位は平均ランクとするランク化（丸め誤差対策に round(..., 12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
    - feature_exploration は標準ライブラリのみで実装（外部依存を避ける設計方針）。
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（MA200 乖離）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から直近の財務データを取得して PER（EPS 非ゼロ時）・ROE を計算。prices_daily / raw_financials のみ参照し外部 API にはアクセスしない。
  - research パッケージの __init__ に主要 API をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - これらの関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照する設計。
- DuckDB スキーマ初期化 (kabusys.data.schema)
  - Raw レイヤーのテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions 等）。
  - テーブル定義に制約（PRIMARY KEY, CHECK）や適切な型（DECIMAL/DATE/TIMESTAMP/BIGINT）を指定。

Security
- ニュース収集で SSRF 対策、XML パースの安全化、レスポンスサイズ制限、URL スキーム検証などを導入。
- J-Quants クライアントで認証トークンの自動リフレッシュと安全なリトライ処理を実装。

Notes / Design decisions
- research の一部（feature_exploration）は外部ライブラリに依存せず標準ライブラリのみで実装しているため、小規模環境でも動作しやすい。
- DuckDB をデータ層に採用し、保存処理は基本的に冪等（ON CONFLICT）になるよう実装している。
- .env の自動ロードはプロジェクトルート探索に基づくため、パッケージ配布後の挙動を考慮してカレントワーキングディレクトリに依存しない設計。
- ニュース記事 ID は URL 正規化後のハッシュを使い、トラッキングパラメータの違いによる重複を防ぐ。

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 上記のセキュリティ節を参照。ネットワーク関連処理には再試行やタイムアウト、リクエスト間隔制御を導入済み。

---

以上がバージョン 0.1.0 の主な追加事項と設計上のポイントです。コードベースの拡張（戦略ロジック、注文実行、監視機能の具体化、さらなるデータソース追加など）は今後のリリースで追記予定です。