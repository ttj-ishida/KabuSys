# Changelog

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog 準拠のフォーマットを採用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回公開リリース。パッケージ名: kabusys, バージョン 0.1.0。

### Added
- パッケージ基盤
  - パッケージ初期化: src/kabusys/__init__.py にてバージョンと公開モジュールを定義。
  - モジュール構成: data, strategy, execution, research, monitoring 等のモジュール群を含む骨組みを提供。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサ: export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントなどに対応。
  - Settings クラス: J-Quants トークン、kabuAPI パスワード、Slack 設定、DB パス（duckdb/sqlite）、環境（development/paper_trading/live）やログレベル検証などのプロパティを提供。
  - 環境値検証（許可される env 値・ログレベルのチェック、未設定時は ValueError）。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装。
  - レート制限遵守（120 req/min の固定間隔スロットリング via _RateLimiter）。
  - 冪等的なデータ保存用の save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。DuckDB への INSERT は ON CONFLICT で更新。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - HTTP リクエスト処理: 最大 3 回のリトライ（指数バックオフ）、408/429/5xx に対する再試行、429 の Retry-After 対応。
  - 401 レスポンス受信時は ID トークンを自動リフレッシュして 1 回リトライするロジック。
  - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
  - 取得時刻（fetched_at）は UTC ISO8601 形式で記録。
  - 入力データ変換ユーティリティ：_to_float / _to_int（厳格な変換／不正値は None）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集・前処理・DB保存の実装。
  - 記事ID は正規化した URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
  - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_*, fbclid など）の除去、フラグメント削除、クエリパラメータのソート。
  - テキスト前処理: URL 除去、空白正規化。
  - XML パース: defusedxml を用いた安全な XML パース（XML Bomb 等の対策）。
  - SSRF 対策:
    - フェッチ前のホストがプライベートアドレスでないことの検査。
    - リダイレクト検査用のカスタムハンドラ (_SSRFBlockRedirectHandler) によりスキーム/プライベートアドレスを事前検証。
    - 非 HTTP/HTTPS スキームを拒否。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - DB 保存: raw_news へのチャンク挿入と INSERT ... RETURNING による新規挿入ID取得、トランザクションでの一括挿入（ロールバック対応）。
  - 銘柄抽出: 本文から 4 桁の銘柄コードを抽出し既知コードセットでフィルタする extract_stock_codes 実装。
  - news_symbols への紐付け保存（個別 & 一括関数: save_news_symbols / _save_news_symbols_bulk）。

- リサーチ / 特徴量探索（src/kabusys/research/*.py）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズンの将来リターンを高速に取得（単一クエリで LEAD を使用）。
    - calc_ic: ファクター値と将来リターン間のスピアマンランク相関（IC）を計算。NULL/非有限値フィルタ、3件未満は None。
    - rank: 平均ランク（同順位は平均ランク）、丸めによる ties の安定化。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算（None を除外）。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。必要データ不足時は None。
    - calc_volatility: atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio を計算。NULL 伝播を考慮した true_range 計算。
    - calc_value: raw_financials から直近の財務データを取得して PER / ROE を計算（EPS が 0/欠損のとき PER は None）。
  - すべて DuckDB 接続と prices_daily / raw_financials テーブルを参照する設計。外部 API にはアクセスしない（Research 環境安全）。

- スキーマ / 初期化（src/kabusys/data/schema.py）
  - DuckDB 用 DDL 定義（Raw Layer の raw_prices, raw_financials, raw_news, raw_executions など）を用意。DataSchema に基づく多層構造（Raw / Processed / Feature / Execution）に対応した設計。

- その他
  - research パッケージの __init__ で、calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank と kabusys.data.stats.zscore_normalize をエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集に関する SSRF 対策、XML パースの安全化（defusedxml）、受信サイズ上限、gzip 解凍後のサイズチェックを実装。
- J-Quants API クライアントで 401 レスポンス受信時にトークン自動リフレッシュを行い、リフレッシュ失敗時は明示的にエラー化。

### Notes / 小さな実装上の注意点
- DuckDB のテーブル名やカラム型、PK 制約に依存するクエリが多数あるため、同名スキーマが存在する前提で動作します。
- news_collector の URL 正規化は既知のトラッキングパラメータプレフィックスのみ除去します。特殊ケースは追加が必要な場合があります。
- jquants_client の _request は urllib を使った実装で、カスタムヘッダやタイムアウトを設定しています。ネットワークの特定環境での挙動は検証が必要です。
- research モジュール各関数は外部ライブラリ（pandas 等）に依存せず標準ライブラリ + DuckDB SQL によって実装されています。大規模データでのパフォーマンスは DuckDB の設定や実行コンテキストに依存します。

---

今後の予定（例）
- Strategy / Execution モジュールの実装（発注ロジック、ポジション管理、kabu API との連携）。
- 追加のデータ取り込みソース、ニュース解析（自然言語処理）や特徴量の拡充。
- テストカバレッジ強化、CI / CD パイプライン整備。

（必要であれば、個別ファイルごとの変更点や設計ドキュメント参照箇所を更に追記します。）