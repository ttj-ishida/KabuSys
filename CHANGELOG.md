CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
（以下の記載は提供されたソースコードの内容から推測して作成しています。）

Unreleased
----------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py にてバージョン "0.1.0" を定義。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数の読み込み機能を実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用途）。
    - .env のパースは export KEY=val 形式、シングル/ダブルクォートとエスケープに対応。
    - 必須設定取得ヘルパー _require と Settings クラスを提供。
    - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）やデフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等）を扱うプロパティを用意。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL のバリデーションを実装。
- Data モジュール（J-Quants クライアント / ニュース収集 / スキーマ）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大試行回数、特定ステータスでのリトライ）を実装。
    - 401 Unauthorized を検出した場合のトークン自動リフレッシュ（1回のみ）を実装。ID トークンをモジュールレベルでキャッシュ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements 実装。
    - fetch_market_calendar 実装。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（冪等化: ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ _to_float/_to_int を提供（不正値を安全に処理）。
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を収集し raw_news テーブルに保存するニュース収集モジュール。
    - セキュリティ対策: defusedxml による XML パース、防SSRF（リダイレクト検査・ホストのプライベートIP検出）、受信サイズ制限（MAX_RESPONSE_BYTES）、gzip 解凍後のサイズ検査（Gzip-bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
    - 記事テキスト前処理（URL 除去・空白正規化）。
    - extract_stock_codes による本文からの 4 桁銘柄コード抽出（known_codes フィルタ付き）。
    - save_raw_news / save_news_symbols / _save_news_symbols_bulk: DuckDB へのチャンク挿入、トランザクション管理、INSERT ... RETURNING を用いることで実際に挿入された件数を正確に返す実装。
    - run_news_collection により複数ソースの収集・保存・銘柄紐付けを統合（ソース単位でエラーハンドリング）。
  - src/kabusys/data/schema.py
    - DuckDB 用スキーマ定義（Raw Layer のテーブル定義を含む）。
    - raw_prices / raw_financials / raw_news / raw_executions などの CREATE TABLE 文（制約・PRIMARY KEY・型チェック付き）を用意。
- Research モジュール（特徴量・因子計算）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns の実装（DuckDB prices_daily を参照、任意ホライズンでのリターン算出）。
    - Information Coefficient（Spearman の ρ）を計算する calc_ic を実装（ランク付けに rank ユーティリティを使用、十分な有効レコードがない場合は None を返す）。
    - factor_summary による基本統計量（count, mean, std, min, max, median）計算。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - src/kabusys/research/factor_research.py
    - ファクター計算関数を実装（prices_daily / raw_financials のみ参照）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を算出。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を算出。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を算出（EPS が 0 または欠損のとき PER は None）。
  - src/kabusys/research/__init__.py にてユーティリティと因子関数を公開。
- Strategy / Execution / Monitoring パッケージ構成
  - src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py, などのパッケージ初期ファイルを追加（将来拡張用のプレースホルダ）。

Changed
- ドキュメント的記述をコード内 docstring として多めに追加（設計方針・安全策・入出力仕様の明確化）。これにより内部 API の意図と制約が明確化。

Fixed
- 該当なし（初回リリースとして新規実装）。

Security
- ニュース収集における複数のセキュリティ対策を導入:
  - defusedxml による XML パース（XML-bomb 等への対策）。
  - リダイレクト先スキーム検査、最終 URL とリダイレクト先のプライベートアドレス検査による SSRF 対策。
  - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズ確認（Gzip-bomb 対策）。
  - URL スキーム検証（http/https のみ許可）。
- J-Quants クライアント側での堅牢なエラーハンドリング・リトライにより外部 API 呼び出しの失敗時の暴走を抑制。

その他 / 注意点
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、prices_daily / raw_* テーブルのみを参照する設計になっているため、本番の発注 API 等にはアクセスしない想定。
- .env パーサーはクォート・エスケープ・インラインコメント等の取り扱いを考慮しており、export KEY=val 形式にも対応。
- save_* 系関数は冪等化を意識しており、重複挿入時に ON CONFLICT を使用して更新/スキップする実装になっている。
- calc_ic 等の統計関数は外部依存（pandas/numpy）を使用せず実装されているため、大量データでの最適化は今後の課題となる可能性あり。

今後の TODO（推奨）
- Strategy / Execution 実装の具体化（発注ロジック、ポジション管理、監視）。
- 大規模データ処理時の性能改善（大量レコード時のメモリ・SQL 最適化、必要なら pandas/numpy の導入）。
- テストカバレッジの追加（特にニュース収集の SSRF テスト、J-Quants API のリトライ挙動、.env パーサーの境界ケース）。
- スキーマ定義の完全化（現状 raw テーブル中心。processed/feature/execution 層の DDL を追加）。

---

注: 上記 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートに含める内容・日付・分類はプロジェクト方針に合わせて調整してください。