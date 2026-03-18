# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のパッケージバージョン: 0.1.0

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース。以下の主要機能・モジュールを実装しました。
  - パッケージ初期化
    - kabusys.__init__: パッケージメタ情報とエクスポート対象（data, strategy, execution, monitoring）を定義。
    - バージョン: 0.1.0

  - 環境変数 / 設定管理 (kabusys.config)
    - .env ファイルおよび環境変数からの自動読み込み機能を実装。
      - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を探索）により、CWDに依存しないロードを実現。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - .env パーサの実装:
      - export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの取り扱い、クォートなしのコメント扱い（直前が空白/タブの場合）等の堅牢な解析を実装。
    - 設定抽象化クラス Settings を提供:
      - J-Quants / kabuAPI / Slack / DB パス等のプロパティを提供。
      - env や log_level の値検証（許容値チェック）を実装。
      - is_live / is_paper / is_dev のユーティリティプロパティを提供。

  - データ取得・永続化 (kabusys.data.jquants_client)
    - J-Quants API クライアントを実装。
      - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
      - ページネーション対応の fetch_* 関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - リトライロジック: 指数バックオフ（最大3回）と特定ステータス（408, 429, 5xx）でのリトライ処理。
      - 401 受信時の ID トークン自動リフレッシュ（1回）をサポート。
      - ID トークンのモジュールレベルキャッシュを実装し、ページネーション中の再利用を最適化。
      - JSON デコード失敗時の明示的エラー報告。
    - DuckDB へ安全に保存するユーティリティを実装:
      - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
      - INSERT ... ON CONFLICT DO UPDATE による冪等保存を採用。
      - fetched_at を UTC ISO8601 形式で記録（look-ahead bias 対策）。
      - 型変換ヘルパー _to_float / _to_int を実装し、受信データの堅牢な正規化を行う。
      - PK 欠損行はスキップし、スキップ件数のログ出力。

  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィードからの記事収集パイプラインを実装。
      - デフォルトソース（Yahoo Finance のカテゴリ RSS）を定義。
      - 安全対策:
        - defusedxml を用いた XML パースで XML Bomb 等への耐性を確保。
        - URL スキーム検証（http/https のみ）、プライベートホスト/ループバック/リンクローカル検出による SSRF 防止。
        - リダイレクト時もスキーム/ホストを検証するカスタムリダイレクトハンドラを実装。
        - レスポンスサイズの上限（MAX_RESPONSE_BYTES = 10MB）を設け、受信段階と gzip 解凍後の両方で検査（Gzip bomb 対策）。
        - トラッキングパラメータ（utm_*, fbclid 等）の除去により正規化された URL から記事ID（SHA-256 の先頭32文字）を生成し、冪等性を担保。
      - テキスト前処理（URL 除去、空白正規化）と pubDate の堅牢なパース。
      - fetch_rss: gzip 圧縮対応、XML パース失敗時のワーニングと空リスト返却。
      - DB への保存:
        - save_raw_news: チャンク分割（_INSERT_CHUNK_SIZE）かつ単一トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、実際に挿入された記事ID を返す。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存をチャンク処理・トランザクションで実装。実挿入件数を正確に返す（RETURNING ベース）。
      - 銘柄抽出ユーティリティ:
        - extract_stock_codes: 正規表現（4桁）による候補抽出と known_codes によるフィルタリング。重複除去を行う。
      - 実行関数 run_news_collection: 複数ソースを順次取得し、失敗ソースはスキップして継続、各ソースごとの新規保存件数を返却。

  - DuckDB スキーマ初期化 / DDL (kabusys.data.schema)
    - DataSchema に基づくスキーマ定義モジュールを追加。
      - Raw Layer のテーブル DDL を実装: raw_prices, raw_financials, raw_news 等（および実行レイヤー用の雛形 raw_executions の定義を含む）。
      - Raw / Processed / Feature / Execution の3層構造設計をドキュメント化。

  - 研究（Research）用ユーティリティ (kabusys.research)
    - 特徴量・ファクター計算モジュールを実装。
      - calc_momentum: 1m/3m/6m のリターン、200日移動平均乖離率を銘柄毎に計算。ウィンドウ不足時は None を返す。
      - calc_volatility: 20日 ATR（true range を正しく扱う）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。ウィンドウ不足時は None を返す。
      - calc_value: raw_financials の target_date 以前で最新の財務データを取得し PER（EPS が有効な場合）・ROE を計算。
      - feature_exploration.calc_forward_returns: target_date の終値から指定ホライズン（営業日）先の将来リターンを一括クエリで取得。ホライズン上限チェック（<=252）を実装。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損や ties の扱い、必要最小レコード数チェック（>=3）を実装。
      - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
      - rank: 同順位は平均ランクで処理（round による丸めで ties 検出の安定化）。
    - 設計方針として DuckDB の prices_daily / raw_financials テーブルのみ参照し、外部 API や発注処理にはアクセスしないことを明記。
    - 依存最小化: pandas 等外部ライブラリに依存せず標準ライブラリ + duckdb で実装。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- ニュース収集部で複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策: スキーム検証（http/https のみ）、プライベートアドレス判定、リダイレクト先の事前検査。
  - レスポンスサイズ制限と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化と追跡パラメータの除去により、ID の冪等性とプライバシー保護を強化。

Notes / Known limitations
- DuckDB のスキーマ定義は Raw Layer の主要テーブルを含むが、Processed/Feature 層の詳細 DDL は今後拡張予定です。
- data.stats.zscore_normalize は kabusys.data.stats に依存しており、統計正規化ユーティリティを研究モジュールで利用しています（当該モジュールの実装は別途）。
- .env パーサは多くのケースを想定したパーシングを行うが、極端な不正フォーマットの .env 行は無視されます。
- jquants_client の rate limiting は単一プロセス内での制御を前提としており、分散環境での共有レート制御は別途対処が必要です。

作者注記
- このリリースは「安全性」「冪等性」「実運用を想定した堅牢性」に重点を置いて実装しています。今後は Processed/Feature 層の拡充、strategy/execution 周りの実装、テストカバレッジの拡大を予定しています。