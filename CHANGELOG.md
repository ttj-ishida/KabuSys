# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]


## [0.1.0] - 2026-03-18
初回リリース。以下の主要機能・実装を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加（__version__ = 0.1.0）。公開APIとして data, strategy, execution, monitoring をエクスポート。

- 設定/環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動で読み込む仕組みを実装。CWD に依存しない探索を行う。
  - .env の行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォートやエスケープ対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - 必須環境変数チェック（_require）と Settings クラスを提供。J-Quants, kabuステーション, Slack, DBパスなどの設定プロパティを用意。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション、is_live/is_paper/is_dev の便利プロパティを追加。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。日次株価、財務諸表、マーケットカレンダーの取得関数を提供（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング(RateLimiter)を実装。
  - 再試行（指数バックオフ、最大3回）ロジックを実装。HTTP 408/429/5xx をリトライ対象に指定。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動更新して1回リトライする仕組みを実装。
  - 取得データを DuckDB に保存する冪等的な保存関数（ON CONFLICT DO UPDATE）を実装（raw_prices / raw_financials / market_calendar）。
  - 文字列→数値変換ユーティリティ（_to_float, _to_int）を実装し、空値・不正値に対する安全な変換を提供。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集機能を追加（デフォルトソース: Yahoo Finance のビジネス RSS）。
  - XML パースに defusedxml を利用して XML Bomb 等の攻撃対策を実装。
  - SSRF 対策：URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことを検査、リダイレクト先の事前検査用ハンドラを導入。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）・gzip 解凍後サイズチェックを実装（メモリ DoS 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）→ SHA-256（先頭32文字）で記事IDを作成し冪等性を担保。
  - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）を実装。
  - raw_news / news_symbols へのトランザクション単位のバルク保存を実装。チャンク化・INSERT ... RETURNING を用いて実際に挿入された件数を正確に返す。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw レイヤーのテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions などの定義を含む）。
  - DDL に対して制約（NOT NULL / CHECK / PRIMARY KEY）を設定しデータ整合性を強化。

- リサーチ・ファクター計算（kabusys.research）
  - 特徴量探索モジュール（feature_exploration）を追加：
    - 将来リターン calc_forward_returns（複数ホライズン対応・1クエリ取得・範囲限定によるスキャン最適化）
    - IC（Information Coefficient）計算 calc_ic（スピアマンの順位相関、データ不足時の None 戻り）
    - ファクター統計サマリー factor_summary、ランク化ユーティリティ rank
    - 標準ライブラリのみでの実装方針を明示（pandas 等に依存しない）
  - ファクター計算モジュール（factor_research）を追加：
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）。営業日ベースのラグ計算を DuckDB のウィンドウ関数で実装。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対ATR(atr_pct)、20日平均売買代金、出来高比率（volume_ratio）。true_range の NULL 伝播を考慮した実装。
    - Value: raw_financials から最新の財務データを取得して PER（EPS に依存）・ROE を計算する処理を実装。
    - 各関数は prices_daily / raw_financials テーブルのみを参照し、本番発注API等へアクセスしない設計。

- パッケージ公開インターフェース（kabusys.research.__init__）
  - 主要ユーティリティとファクター計算関数を __all__ で公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Security
- news_collector において SSRF 対策、defusedxml による XML ハードニング、レスポンスサイズチェックを導入。
- J-Quants クライアントはトークン管理・自動リフレッシュ、再試行ロジックを備え、失敗耐性を向上。

### Performance
- calc_forward_returns 等の集計は可能な限り単一クエリで取得するよう最適化（ウィンドウ関数活用）。
- news_collector の DB 保存はチャンク化してバルクINSERTを行いトランザクション回数を削減。
- J-Quants API 呼び出しは固定間隔でスロットリングしレート制限を厳守。

### Internal / Developer
- .env パーサは export プレフィックス、クォート内エスケープ、インラインコメントの取り扱い等の仕様を実装して互換性を高めた。
- settings により環境（development/paper_trading/live）を厳格に扱い、ログレベルの妥当性チェックを追加。
- モジュール内ロギングを強化（各主要処理で取得件数や警告をログ出力）。

### Known limitations / Notes
- DuckDB を利用するため、実行環境に duckdb ライブラリと DB ファイルへの書込権限が必要。
- research モジュールは標準ライブラリのみで実装しているため、大規模データ処理の柔軟性は将来の依存導入で拡張する可能性あり。
- PBR・配当利回りなど一部バリューファクターは未実装（calc_value で明記）。
- raw_executions テーブル定義など一部スキーマは継続実装を想定（コードベースの一部に続きあり）。

---

変更内容に誤りや補足が必要な点があればお知らせください。コードベースから推測した内容を元に記載しています。