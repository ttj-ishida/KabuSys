# Changelog

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的なルール:
- 互換性のある変更は "Changed"、機能追加は "Added"、バグ修正は "Fixed"、セキュリティ対応は "Security" に記載します。
- 初版リリースのため過去の履歴はありません。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。バージョンは 0.1.0。
  - package-level __all__ に data / strategy / execution / monitoring を公開（strategy/execution は初期は空パッケージとして配置）。

- 環境設定管理（kabusys.config）
  - .env ファイルか OS環境変数から設定値を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env のパース機能を実装（export プレフィックス対応、クォートやインラインコメントの考慮）。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）を提供する Settings クラス。
  - 環境（development / paper_trading / live）とログレベルの検証ロジックを実装。
  - データベースの既定パス（DUCKDB_PATH / SQLITE_PATH）のデフォルトを提供。

- Data レイヤー（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）
    - レート制限（120 req/min）を満たす固定間隔スロットリング実装（内部 _RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時は自動でリフレッシュトークンから ID トークンを再取得して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes、save_financial_statements、save_market_calendar）。
    - 入出力変換ユーティリティ（_to_float、_to_int）。
  - ニュース収集（data/news_collector.py）
    - RSS フィード収集、記事前処理、正規化、DB 保存（raw_news）、銘柄紐付け（news_symbols）のワークフローを実装。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）を実装。
    - RSS の取得に際して以下の防御措置を実装:
      - defusedxml を利用した XML パース（XML Bomb 対策）。
      - SSRF 対策（許可スキームは http/https のみ、リダイレクト先の事前検査、プライベートアドレスの検出・拒否）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の検査。
    - DB への保存時はチャンク/トランザクションを用い、INSERT ... RETURNING で実際に挿入された件数を返す。
    - 銘柄コード抽出ユーティリティ（4桁数値抽出、既知コードセットによるフィルタリング）。
    - 全ソースをまとめて収集する run_news_collection を提供。

- Research レイヤー（kabusys.research）
  - feature_exploration モジュール
    - calc_forward_returns: DuckDB の prices_daily テーブルを参照して任意ホライズンの将来リターンを一括計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを与えるランク関数（丸め誤差対処のため round(v, 12) を利用）。
    - factor_summary: カラムごとの基本統計（count/mean/std/min/max/median）を計算。
    - 設計上、標準ライブラリのみ依存（pandas 未使用）で、DuckDB 接続を受け取る形。
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）を計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR（atr_20）、ATR の相対値（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新の財務データを得て PER（EPS が 0/欠損時は None）、ROE を計算。
    - 各関数は (date, code) ベースの dict リストを返す設計。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw Layer のテーブル定義（raw_prices, raw_financials, raw_news, raw_executions など）の DDL を追加（CREATE TABLE IF NOT EXISTS）。
  - データレイヤのスキーマ管理／初期化を想定した設計を開始。

### Security
- news_collector にて以下のセキュリティ対策を追加
  - defusedxml による XML パース（外部攻撃/エンティティ注入対策）。
  - SSRF 対策: URL スキーム検査、プライベート IP/ホストの検出と拒否、リダイレクト先事前検証。
  - RSS レスポンスの最大サイズや gzip 解凍後サイズチェックによる DoS 対策。

### Notes / ドキュメント的な注意
- 環境変数に関する注意:
  - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。未設定時は Settings が ValueError を送出します。
  - .env.example を参考に .env を作成することが期待されます。
- DuckDB のテーブル（prices_daily / raw_financials / raw_prices 等）は本リリースの機能で参照・更新されます。初期化スクリプトで schema モジュールの DDL を実行してください。
- research モジュールは本番の注文/発注 API にはアクセスしない設計です（分析・リサーチ用）。
- jquants_client は API レート制限・リトライ・トークン自動更新を実装していますが、実行環境のネットワーク設定や API 利用制限に注意してください。

### Deprecated
- なし

### Breaking Changes
- 初回リリースのため該当なし

---

今後の予定（例）
- strategy / execution / monitoring の実装と統合テスト
- Feature 層（特徴量保存テーブル）の正式DDLと ETL 実装
- 単体テスト・CI の整備、ドキュメント補強（Usage/Deployment 手順）

--- 

（補足）本 CHANGELOG はリポジトリ内のコード構成・コメントから推測して作成しています。実際のリリースノートに含める文言や日付は必要に応じて調整してください。