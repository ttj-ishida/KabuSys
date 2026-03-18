CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧 (__all__) を定義。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - プロジェクトルート検出ロジック (_find_project_root) は .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env パーサ (_parse_env_line) は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
    - .env 読み込みは優先順位 OS 環境 > .env.local > .env、override/protected 機能で既存 OS 環境の保護に対応。
    - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベルなどのプロパティ経由で取得可能（入力検証付き、is_live/is_paper/is_dev のヘルパあり）。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - 固定間隔スロットリングによるレート制限実装 (_RateLimiter, 120 req/min)。
    - リトライロジック（指数バックオフ、最大3回）および 408/429/5xx に対する再試行。
    - 401 発生時の ID トークン自動リフレッシュ（1回のみ）とトークンキャッシュ管理。
    - 汎用 HTTP ユーティリティ _request により JSON デコード、エラー処理、Retry-After 処理を実装。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を提供（ON CONFLICT DO UPDATE による重複排除）。
    - データ正規化ユーティリティ _to_float / _to_int を実装（空値や変換失敗を None にする、安全な数値変換ロジック）。

- ニュース収集・処理
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と記事保存の統合モジュールを実装。
    - fetch_rss:
      - URL 正規化・検証（http/https 限定）、初期ホスト検査およびリダイレクト先検査による SSRF 対策。
      - defusedxml による XML パース（XML Bomb 等への防御）。
      - Content-Length / 実読み込みバイト数の上限チェック（MAX_RESPONSE_BYTES＝10MB）および gzip 解凍後のサイズ検証。
      - title/content の前処理（URL 除去、空白正規化）。
      - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - DB 保存:
      - save_raw_news: チャンク分割・トランザクション・INSERT ... RETURNING による新規挿入 ID の正確取得。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コード紐付けの一括保存（重複除去、チャンク挿入、トランザクション）。
    - 銘柄コード抽出 (extract_stock_codes): 正規表現で4桁数字候補を抽出し、known_codes フィルタで有効コードのみ返す。
    - run_news_collection: 複数 RSS ソースの収集を個別に処理し、部分失敗に対しても継続する堅牢な統合ジョブ。

- 研究（Research）モジュール: ファクター計算・探索
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズン（デフォルト 1/5/21）に対する将来リターンを一括 SQL で計算。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク）相関を計算。データ不足や非有限値を排除して安全に計算。
    - rank: 同順位は平均ランク処理、丸めによる ties 検出漏れ対策。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - 設計方針として pandas 等の外部ライブラリに依存せず標準ライブラリ + duckdb で実装。

  - src/kabusys/research/factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev の計算（ウィンドウ不足時は None）。
    - calc_volatility: 20日 ATR（atr_20）、atr_pct、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御に注意）。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算（EPS が 0/欠損の場合は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API へアクセスしない設計。

  - src/kabusys/research/__init__.py
    - 上記関数群と zscore_normalize（kabusys.data.stats から）がパッケージ公開されるよう export 設定。

- スキーマ定義（DuckDB）
  - src/kabusys/data/schema.py
    - Raw Layer のテーブル DDL 定義を追加: raw_prices, raw_financials, raw_news, （raw_executions の定義着手）。
    - DataLayer の設計ノート（Raw / Processed / Feature / Execution）を含む初期スキーマモジュール。

Security
- XML パースに defusedxml を利用、RSS 処理時に XML 攻撃対策を導入。
- RSS フェッチ時にスキーム検証・プライベートアドレス検査・リダイレクト検査を行い SSRF 対策を実装。
- HTTP レスポンスサイズ制限と gzip 解凍後サイズチェックでメモリ DoS を軽減。

Performance / Reliability
- API 呼び出しに対して固定間隔のレートリミットを導入し、J-Quants のレート上限を尊重。
- リトライ + 再試行間隔（指数バックオフ）を備え、429 の Retry-After を優先。
- DB 書き込みはチャンク化・トランザクション化し、INSERT ... RETURNING を用いて実際に挿入された件数を正確に把握。
- DuckDB のウィンドウ関数を活用して一度の SQL で大量銘柄の計算を行いパフォーマンスを改善。

Breaking Changes
- なし（初回リリース）

Notes / Usage Tips
- 自動 env ロードは開発時便利だが、CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- research モジュールは外部 API にアクセスしないため、ローカルの DuckDB に prices_daily / raw_financials が揃っていれば結果を再現可能。
- news_collector.run_news_collection に渡す known_codes を用いると記事に含まれる 4 桁銘柄コードを既知コードでフィルタして紐付け可能。

Acknowledgements
- 本リリースでは設計ドキュメント（DataPlatform.md, StrategyModel.md, DataSchema.md 等）に基づく実装方針を反映しています。

----