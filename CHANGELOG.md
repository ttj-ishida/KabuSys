# CHANGELOG

すべての重大な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

なお本リポジトリの初回リリースとしての変更点を、コードベースから推定してまとめています。

## [0.1.0] - 2026-03-20

### Added
- パッケージ基盤
  - パッケージのバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 主要サブモジュールを公開（data, strategy, execution, monitoring）。

- 設定 / 環境管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロードを実現。
  - .env / .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。.env.local は上書き（override）される。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - .env パースの堅牢化：
    - コメント行／空行の扱い、export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメント除去の正確化。
    - クォート無し値における inline コメント判定の細かい挙動制御。
  - 必須環境変数取得ヘルパ _require と Settings クラスを提供：
    - J-Quants / kabuステーション / Slack / DB パス 等の設定プロパティを実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値の検証とエラー通知）。
    - 設定の便宜プロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx の再試行対応。
    - 401 発生時の自動トークンリフレッシュ（1 回限定）とトークンキャッシュの共有。
    - ページネーション対応（pagination_key を用いた継続取得）。
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar の取得関数。
  - DuckDB への保存ユーティリティ：
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装し冪等性を確保（ON CONFLICT DO UPDATE / DO NOTHING を使用）。
    - レコード整形と型変換ユーティリティ（_to_float / _to_int）。
    - fetched_at を UTC ISO8601 で記録して取得時刻をトレース可能に。
    - PK 欠損行のスキップとログ警告を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と raw_news テーブル保存のための基盤を実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - セキュリティ対策：
    - defusedxml を利用して XML Bomb 等を防御。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を緩和。
    - トラッキングパラメータのリスト化（utm_*, fbclid 等）。
    - バルク INSERT のチャンク処理 (_INSERT_CHUNK_SIZE)。
  - デフォルト RSS ソース定義（例: Yahoo Finance）。

- リサーチ（kabusys.research）
  - ファクター計算・探索ユーティリティを実装・公開：
    - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）。
    - zscore_normalize を既存のデータモジュールから公開（data.stats 経由）。
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）。
    - calc_ic（Spearman のランク相関による Information Coefficient 計算）。
    - factor_summary（count/mean/std/min/max/median の統計要約）。
    - rank（同順位は平均ランクとするランク付けユーティリティ）。
  - 各関数は外部ライブラリに依存せず、DuckDB SQL + 標準ライブラリで実装されている旨を明記。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装：research モジュールの生ファクターを統合し features テーブルに保存するワークフロー。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - Z スコア正規化（対象列は _NORM_COLS）、±3 のクリップで外れ値を制御。
    - target_date 単位で削除→挿入の置換（トランザクションで原子性を保証）。
    - 休場日・当日欠損に対応する最新価格参照ロジック。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装：features / ai_scores / positions を参照して BUY/SELL シグナルを生成し signals テーブルへ保存。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）算出ロジック。
    - シグモイド変換、欠損値は中立値 0.5 で補完するポリシー。
    - デフォルト重み (_DEFAULT_WEIGHTS) と閾値 (_DEFAULT_THRESHOLD=0.60)、ユーザ与重みの検証・正規化（合計が 1.0 になるようリスケール）。
    - Bear レジーム検出（AI の regime_score の平均が負でかつサンプル数が閾値以上）により BUY を抑制。
    - SELL 生成ロジック（ストップロス: 終値 / avg_price - 1 < -8%、final_score が閾値未満など）。トレーリングストップ等の未実装機能を明示。
    - 保有銘柄の価格欠損時は SELL 判定をスキップしログ警告。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性）。

### Changed
- （初回リリースのため該当なし）パッチ的な変更履歴はなし。

### Fixed
- （初回リリースのため該当なし）既知のバグ修正履歴はなし。

### Security
- news_collector で defusedxml の利用、受信サイズ制限、URL 正規化により外部入力に対する安全性向上を図った。
- jquants_client のトークン管理と HTTP エラー処理を慎重に扱い、意図しないトークン再帰呼び出しを防止する guard を実装。

### Notes / Known limitations
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date が必要。
- calc_forward_returns はホライズンを営業日ベースで扱う設計だが、週末・祝日対応のためクエリ範囲にバッファを取っている点に注意。
- NewsCollector の記事 ID は URL 正規化後のハッシュなどで冪等性を担保する設計想定（実装の続きが存在する可能性あり）。
- .env パーサは多くのケースを考慮しているが、極端なケースは未網羅の可能性あり。自動ロードは環境に応じて無効化可能。

---

以上がコードベースから推定した 0.1.0 初回リリースの主要な変更点のサマリです。追加で、各関数の公開 API（引数/返り値）を一覧化するなど詳細な CHANGELOG 表現が必要であれば対応します。