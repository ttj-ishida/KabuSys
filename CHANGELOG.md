CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。複数のコンポーネント（data / research / strategy / execution / monitoring）を含む初期リリースです。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース "kabusys"（__version__ = 0.1.0）。
  - メインモジュール: kabusys
  - 公開サブパッケージ: data, strategy, execution, monitoring（strategy, execution の __init__ はプレースホルダ）

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）
  - .env パーサ実装（コメント処理、export プレフィックス、クォート／エスケープ対応）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラス実装（J-Quants、kabu API、Slack、DBパス、実行環境・ログレベル検証など）
  - 環境値検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）
  - Path 型でのデータベースパス取得（duckdb/sqlite）

- Data レイヤー（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 固定間隔スロットリングによるレート制限制御（120 req/min）
    - 再試行ロジック（指数バックオフ、最大試行回数、429 の Retry-After 対応）
    - 401 に対する自動トークンリフレッシュ（1 回のみ）と ID トークンキャッシュ
    - fetch_* 系: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
    - DuckDB への冪等保存機能: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ: _to_float, _to_int
    - 設計ノート: fetched_at に UTC タイムスタンプを記録し Look-ahead Bias を抑制

  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィード取得と記事整形（デフォルトで Yahoo Finance ビジネス RSS を含む）
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等の防御）
      - SSRF 対策（リダイレクト検査・ホストプライベートアドレス拒否）
      - URL スキーム検証（http/https のみ）
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後の再検査
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 記事IDを正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
    - raw_news へのバルク保存（INSERT ... RETURNING を用いて実際に挿入された ID を返す）
    - news_symbols（記事と銘柄の紐付け）保存のバルク処理（チャンク化、トランザクション）
    - 銘柄コード抽出ユーティリティ（4桁数字パターン、known_codes によるフィルタ）
    - run_news_collection による全ソース収集ワークフロー（個々のソースは独立してエラーハンドリング）

  - DuckDB スキーマ定義（kabusys.data.schema）
    - Raw レイヤー用テーブル DDL 定義の実装（raw_prices, raw_financials, raw_news, raw_executions 等の作成文を含む）
    - DataSchema に従った 3 層（Raw / Processed / Feature / Execution）の方針を明記

- Research レイヤー（kabusys.research）
  - feature_exploration モジュール
    - calc_forward_returns: DuckDB の prices_daily を用いて複数ホライズンの将来リターンを一度に取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（欠損・finite チェック、最小サンプルチェック）
    - rank: 同順位は平均ランクを返すランク関数（丸めによる ties を考慮）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - 設計方針: DuckDB の prices_daily テーブルのみ参照、外部ライブラリに依存しない実装

  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を DuckDB のウィンドウ関数で算出。データ不足時は None を返す
    - calc_volatility: 20日 ATR, 相対 ATR (atr_pct), 20日平均売買代金 (avg_turnover), volume_ratio を計算
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損なら None）、ROE を算出。最新財務レコードの取得は report_date <= target_date の最新を採用
    - 設計方針: DuckDB の prices_daily / raw_financials のみを参照し本番発注 API にはアクセスしない

- ユーティリティ・設計ノート
  - research モジュールは pandas 等の外部ライブラリに依存しない（軽量でトレースしやすい計算を優先）
  - 多くの DB 操作を冪等化（ON CONFLICT / DO UPDATE / DO NOTHING）して再実行可能性を確保
  - ネットワーク関連は urllib を使用した同期実装（シンプルな挙動、テスト用のフックを提供）

Security
- news_collector における SSRF 対策・XML パースの安全化・レスポンスサイズ制限を実装
- J-Quants クライアントにおけるトークン管理と自動リフレッシュによる認証強化

Changed
- 初回リリースのため該当項目なし

Fixed
- 初回リリースのため該当項目なし

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- research の実装は標準ライブラリ中心であり、大規模データ処理や最適化上の要件がある場合は pandas や numpy の採用を検討する必要があります。
- jquants_client は同期 HTTP（urllib）実装のため、大量並列取得を行う用途では別途非同期実装や外部ジョブ制御が必要です。
- schema の raw_executions 定義はファイルの範囲で一部を含んでいます。実運用前に全テーブル定義とインデックス等の確認を推奨します。
- Slack / kabu ステーション周りの実行・発注ロジック（execution, monitoring 等）はこのバージョンでは未実装（パッケージ構造は用意済み）。

以上。