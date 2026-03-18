CHANGELOG
=========

すべての変更点は「Keep a Changelog」形式に従って記載しています。  
重大な変更や後方互換性のある点は各リリースにまとめています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-18
-------------------

初期リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。
以下はコードベースから推測される主要な追加機能と設計方針の要約です。

Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - サブパッケージの公開: data, strategy, execution, monitoring を __all__ で公開。

- 設定 / 環境管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に検出。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - POSIX 風の .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、インラインコメント処理、エスケープ対応）。
  - 環境変数読み出し用 Settings クラスを提供（jquants_refresh_token, KABU_API_PASSWORD, Slack トークン/チャンネル, DB パス等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の定義）および便利な is_live/is_paper/is_dev プロパティ。

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行（指数バックオフ）ロジック、HTTP 429/408/5xx ハンドリング。
    - 401 受信時の自動トークンリフレッシュ処理（1回のみの再試行を保証）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT で上書き。
    - 型変換ユーティリティ (_to_float/_to_int) とモジュールレベルの id_token キャッシュ。
    - fetched_at を UTC で記録し、Look-ahead Bias を抑制する設計。
  - ニュース収集（data/news_collector.py）
    - RSS フィード収集パイプライン（fetch_rss / run_news_collection）。
    - URL 正規化（トラッキングパラメータ削除、ソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
    - defusedxml による安全な XML パース、gzip 対応、受信サイズ上限（10MB）による DoS対策。
    - SSRF 対策: スキーム検証（http/https のみ）、リダイレクト先のホストがプライベートかどうかの検査、カスタムリダイレクトハンドラ。
    - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）。
    - DuckDB への冪等保存（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。チャンク挿入・トランザクションまとめ・INSERT ... RETURNING による実挿入数取得。
  - スキーマ定義（data/schema.py）
    - DuckDB 用のテーブル定義（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）。
    - Raw / Processed / Feature / Execution のレイヤ分割に基づく設計方針。

- 研究用ユーティリティ（kabusys.research）
  - 特徴量探索（research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: DuckDB の window 関数を用いた高速取得、複数ホライズン一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関の実装（ランク付け補助関数 rank を含む）。欠損値・非有限値を除外、少数レコード時は None を返す。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - ファクター計算（research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算する calc_momentum。
    - Volatility / Liquidity: 20日 ATR, ATR比率, 20日平均売買代金, 出来高比率を計算する calc_volatility（true range の NULL 伝播制御等を考慮）。
    - Value: 最新の財務データ（raw_financials）と株価を組み合わせて PER / ROE を計算する calc_value（報告日以前の最新レコード取得を考慮）。
    - 上記は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照する設計（外部 API へアクセスしない）。
  - research パッケージ初期化で主要関数を __all__ にて公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- その他
  - data/news_collector における既知銘柄抽出・紐付けのための extract_stock_codes 提供。
  - 複数モジュールでロギングを導入しデバッグ/運用時の可観測性を確保。

Changed
- 初回リリースのため履歴なし。

Fixed
- 初回リリースのため履歴なし。

Security
- defusedxml による XML パースの安全化、SSRF 対策、レスポンスサイズ上限など、外部データ取り込みに関する安全対策を多数導入。

Notes / Design decisions
- DuckDB を中心としたオンディスク分析基盤（raw / processed / feature 層）を想定。
- API 呼び出しはレート制御・リトライ・トークン管理を組み合わせて堅牢に設計。
- Research/Strategy 層は外部副作用（発注等）を行わない純粋な計算モジュールとして実装。
- .env の自動読み込みはプロジェクトルートを基準に行い、配布後の動作やテストでの制御を意識した実装。

Acknowledgements
- 初期実装として、データ取得／保存、要点となる特徴量計算、ニュース収集の基本パイプラインを揃えています。今後は strategy / execution / monitoring の各レイヤを拡充し、より多くのファクター・評価指標・運用機能を追加していくことが想定されます。

---