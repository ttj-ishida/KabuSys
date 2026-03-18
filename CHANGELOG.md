CHANGELOG
=========

本書は Keep a Changelog の形式に準拠しており、コードベースから推測できる機能追加・修正・設計方針をまとめた変更履歴です。
（注: 実際のコミット履歴がないため、内容はソースコードの実装から推測して記載しています）

フォーマット
------------
- 変更はセクションごと（Added, Changed, Fixed, Security 等）に分類しています。
- 各項目は該当するモジュールや主な挙動を示します。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-18
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定/読み込み周り（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パース機能を実装（export KEY=val 形式対応、引用符付き値のエスケープ考慮、インラインコメントの取り扱い）
  - .env.local は .env の上書きとして優先読み込み（ただし OS 環境変数は保護）
  - Settings クラスを追加し、アプリケーション全体で参照できる設定 API を提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）
  - KABUSYS_ENV / LOG_LEVEL の検証機構を実装（許容値検査、無効値は ValueError 投げる）
  - duckdb/sqlite のデフォルトパス設定を提供

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - レート制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）
    - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx 対象）を実装
    - 401 受信時はリフレッシュトークンにより id_token を自動更新して 1 回リトライする仕組みを実装
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements を実装
    - DuckDB への保存用関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）
      - 挿入は冪等性を保つため ON CONFLICT DO UPDATE を使用
      - 型変換ユーティリティ (_to_float / _to_int) を提供
    - fetched_at（UTC）を記録して look-ahead bias 対策を考慮

  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィード収集機能を実装（fetch_rss）
      - XML パースに defusedxml を利用する想定（XML Bomb 対策）
      - HTTP(S) スキームのみ許可、SSRF 対策としてプライベートアドレス/ループバックのブロックを実装
      - リダイレクトハンドラでリダイレクト先の検証を実施（_SSRFBlockRedirectHandler）
      - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を超える場合はスキップ（gzip 解凍後もチェック）
      - User-Agent / gzip 対応、Content-Length の事前チェックを実装
      - URL 正規化（トラッキングパラメータ除去、クエリキーソート、フラグメント除去）と SHA-256（先頭32文字）による記事 ID 生成
      - 記事テキスト前処理（URL 除去、空白正規化）を提供
      - 銘柄抽出機能（4桁の数字パターン + known_codes によるフィルタ）を実装
    - DB への保存関数を実装（save_raw_news / save_news_symbols / _save_news_symbols_bulk）
      - INSERT ... RETURNING を使って実際に挿入された件数/ID を返す（重複は ON CONFLICT でスキップ）
      - チャンク分割（_INSERT_CHUNK_SIZE）および 1 トランザクションでの処理により効率化
    - 統合収集ジョブ run_news_collection を実装（各ソース独立でエラーハンドリング、銘柄紐付け処理を含む）

  - DuckDB スキーマ定義・初期化（kabusys.data.schema）
    - Raw Layer のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等）
    - テーブルの型制約・PRIMARY KEY を設計（データ整合性重視）
    - スキーマは DataSchema.md に基づく 3 層構成（Raw / Processed / Feature / Execution）の方針を反映

- Research 層（kabusys.research）
  - feature_exploration モジュールを追加
    - calc_forward_returns: DuckDB の prices_daily テーブルを参照して将来リターン（複数ホライズン）を一度に取得する実装
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算する実装（ランク計算、欠損除外、最小サンプルチェック）
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算するユーティリティ
    - rank: 同順位は平均ランクとするランク関数（丸め対策あり）
    - 設計方針として pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装

  - factor_research モジュールを追加
    - calc_momentum: mom_1m / mom_3m / mom_6m と 200 日移動平均乖離率（ma200_dev）を計算
      - スキャン範囲バッファを設け、LAG/AVG ウィンドウを使って効率的に取得
    - calc_volatility: 20 日 ATR（true range の平均）や相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算
      - 真のレンジ（true_range）は high/low/prev_close の NULL 伝播を考慮して算出
      - 欠損や行数不足時に None を返す方針
    - calc_value: raw_financials から target_date 以前の最新財務情報を取り出して PER / ROE を計算
      - 最新財務レコードの選択に ROW_NUMBER を利用し、prices_daily と結合

- 設計方針・品質
  - Research 関数群は本番発注 API へはアクセスしない（DuckDB のテーブルのみ参照）
  - 冪等性を重視した DB 操作（ON CONFLICT）とトランザクション管理
  - ネットワークの堅牢性（リトライ、タイムアウト、レスポンスサイズ制限、SSRF 対策）
  - ロギングを各モジュールに導入して可観測性を確保

Security
- news_collector において SSRF 対策と XML パースに対する防御（defusedxml 使用想定）を実装
- RSS の受信サイズ制限（10MB）および gzip 解凍後のチェックを実装して DoS/Bomb 対策を講じる
- J-Quants クライアントは 401 発生時に id_token を自動リフレッシュするが、無限再帰を避けるため allow_refresh フラグで保護

Changed
- 初期リリースのため該当なし（初回の機能追加に相当）

Fixed
- 初期リリースのため該当なし

Deprecated
- なし

Removed
- なし

Notes / Usage 例（抜粋）
- 設定参照:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path など

- Research:
  - from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
  - DuckDB 接続を渡して呼び出す設計（外部 API 呼び出しなし）

- データ取得 / 保存:
  - id_token は get_id_token() で取得可能（settings の refresh token を利用）
  - fetch_daily_quotes()/fetch_financial_statements() で API から取得し、save_daily_quotes()/save_financial_statements() で DuckDB に冪等保存

補足
- この CHANGELOG はソースコードの実装内容に基づいて推測して作成しています。実際のリリースノートとして公開する場合は、コミット履歴やリリース作業に基づいて適宜修正してください。