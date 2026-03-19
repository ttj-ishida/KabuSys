# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に従います。  
このプロジェクトはセマンティック バージョニングを採用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。

### Added
- パッケージの骨組みを追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring を公開

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応
  - .env パーサ実装（export 形式、クォート・エスケープ、インラインコメントの取り扱いなどに対応）
  - Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / 環境・ログレベル検証）
  - env 値検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）と is_live/is_paper/is_dev ヘルパー

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装
    - レート制限 (120 req/min) を守る固定間隔 RateLimiter
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）
    - 401 受信時はリフレッシュトークンを使って自動で ID トークンを再取得し1回リトライ
    - ページネーション対応（pagination_key の反復取得）
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等性のため ON CONFLICT DO UPDATE を使用
    - 取得時刻（fetched_at）を UTC で記録（Look-ahead bias のトレース用）
  - 型変換ユーティリティ実装: _to_float / _to_int（空値や不正値を安全に None として扱う）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と前処理の実装（fetch_rss, preprocess_text）
    - defusedxml を使用した安全な XML パース（XML Bomb 対策）
    - gzip 圧縮対応およびレスポンスサイズ上限チェック（MAX_RESPONSE_BYTES, デフォルト 10MB）
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
    - SSRF 対策:
      - fetch 時にスキームの検証（http/https のみ）
      - プライベート/ループバック/リンクローカル/マルチキャストアドレスの検出と拒否
      - リダイレクト時にもスキーム・ホスト検証を行うカスタム RedirectHandler を使用
    - レスポンスの事前 Content-Length チェックと実際の読み込みの両方でサイズ制限を適用
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を使用して実際に挿入された記事IDを返す（チャンク化してトランザクションで処理）
    - save_news_symbols / _save_news_symbols_bulk: news と銘柄（code）紐付けをチャンク化して冪等保存（ON CONFLICT DO NOTHING）
    - 銘柄抽出: テキストから 4 桁の銘柄コードを抽出し既知コードセットでフィルタ（extract_stock_codes）
    - run_news_collection: 複数 RSS ソースを順次収集し DB に保存、個別ソース失敗時にも他ソースへ影響を与えない設計

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema.md に基づく 3 層構造のテーブルを定義する DDL を追加（Raw / Processed / Feature / Execution の考え方を採用）
  - Raw 層のテーブル DDL を実装:
    - raw_prices（株価生データ）
    - raw_financials（生財務データ）
    - raw_news（ニュース生データ）
    - raw_executions（発注・約定の生データ、定義開始）

- リサーチ用ファクター・ユーティリティ（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズンへの将来リターンを DuckDB の prices_daily テーブルから一度のクエリで取得
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（欠損・非有限値を除外、サンプル数が少なければ None を返す）
    - rank: 同順位は平均ランクを採るランク付け（丸め誤差対策で round(v,12) を用いる）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None を除外）
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）を計算（必要行数不足時は None）
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算
    - calc_value: raw_financials から直近財務データを結合し PER/ROE を計算（EPS=0や欠損時は None）
  - research パッケージの __all__ に主要関数を公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank とデータ正規化ユーティリティ zscore_normalize を参照）

### Security
- ニュース収集における複数の安全対策を導入
  - defusedxml による XML パース（外部悪意ある XML に対する防御）
  - SSRF 対策（スキーム検証、プライベート/ループバックアドレスの判定、リダイレクト検査）
  - レスポンスサイズ制限と Gzip 解凍後の検査（DoS / Gzip bomb 対策）

### Notes / Implementation details
- DuckDB を中心としたオンプロセスDB設計を採用。データ取得→raw テーブルに冪等保存→加工/特徴量計算の流れを想定
- J-Quants クライアントはトークンの自動キャッシュ・共有を行いページネーション間でのトークン再利用を最適化
- .env パーサは実運用で遭遇しうる様々な記法（export プレフィックス、クォート・エスケープ、インラインコメント）に対応
- research 側は外部ライブラリ（pandas 等）に依存しない実装方針（標準ライブラリと DuckDB の SQL を併用）

今後の予定（予定事項の例）
- processed / feature 層の DDL 完全実装およびマイグレーションユーティリティ
- strategy / execution / monitoring 各モジュールの実装（発注ロジック、実行監視、Slack 通知等）
- 単体テストとCI導入、各種エラーケースの網羅的テスト

---

参照:
- バージョンは kabusys.__version__ = "0.1.0" に合わせています。