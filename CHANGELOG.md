CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
主な初期実装をまとめたリリースノートです。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージルート: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応。
  - .env の行パーサを実装（コメント, export プレフィックス, クォート内エスケープ, インラインコメント処理など）。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得（J-Quants, kabuAPI, Slack, DB パス, 環境 / ログレベル判定など）。
  - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。
- Data 層（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限制御（固定間隔スロットリング、デフォルト120 req/min）。
    - リトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx を対象）。
    - 401 受信時はトークン自動リフレッシュを行い1回だけリトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への保存用ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）：fetched_at を UTC で記録、ON CONFLICT を使った冪等保存。
    - 型変換ユーティリティ (_to_float / _to_int) を実装（空文字や不正値を安全に None に）。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得と前処理パイプライン（URL 正規化、トラッキングパラメータ削除、テキスト正規化）。
    - セキュリティ対策: defusedxml による XML パース、SSRF 向けのリダイレクト検査、プライベート IP／ループバックの拒否、許容スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック、受信バイト数制限による DoS 緩和。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - DB 保存: raw_news へのバルク挿入（チャンク化、INSERT ... ON CONFLICT DO NOTHING RETURNING を使用し、実際に挿入された ID を返却）。
    - 銘柄コード抽出（4桁数字）と news_symbols への紐付けを一括保存するジョブ run_news_collection を実装。
- Research 層（src/kabusys/research）
  - 特徴量探索・ファクター計算モジュールを実装。
    - feature_exploration.py
      - calc_forward_returns: DuckDB の prices_daily を参照して将来リターン（デフォルト [1,5,21] 営業日）を一括で算出。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（ties 対応、有効レコード数が3未満は None）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
      - rank: 同順位は平均ランクとするランク化実装（丸め誤差対策として round(v,12) を使用）。
      - 設計上、外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで動作。
    - factor_research.py
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。データ不足時は None を返すロジックを含む。
      - calc_volatility: 20日ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
      - calc_value: raw_financials から target_date 以前の最新財務を結合し PER / ROE を計算（EPS が 0/欠損なら PER は None）。
    - research パッケージ __init__.py で主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - すべての research 関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照し、本番口座や発注 API にはアクセスしない設計。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw レイヤーのテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等）。
  - スキーマ初期化／宣言用モジュールを用意（DDL はチェック制約や PK を含む）。

Changed
- 初期リリースのため変更履歴なし。

Fixed
- 初期リリースのため修正履歴なし。

Security
- news_collector: defusedxml を用いた XML パース、SSRF 防止のためのリダイレクト検査とプライベートアドレス拒否、レスポンスサイズ制限など複数の安全対策を実装。
- jquants_client: 401 時のトークン自動リフレッシュ制御により無限再帰を防止する設計（allow_refresh フラグの利用）。

Notes / Known limitations
- strategy/ と execution/ のパッケージは初期コミットでは __init__.py のみで実装がありません（将来の拡張領域）。
- research モジュールは標準ライブラリ実装のため、大量データや高度な統計処理では pandas 等を使った実装に比べて性能上の差異があり得ます。
- DuckDB に依存する関数は DuckDB の接続オブジェクトを引数に取るため、呼び出し側で接続とテーブルが適切に初期化されている必要があります。
- jquants_client の API ベース URL は _BASE_URL で設定。settings によるトークン供給が必須（JQUANTS_REFRESH_TOKEN）。

補足
- 環境変数の自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール環境では明示的に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化することが可能です。
- DuckDB への保存関数は ON CONFLICT による冪等性を備えています。news_collector 側は INSERT ... RETURNING を多用し、実際に挿入されたレコード数を正確に取得します。

-- END --