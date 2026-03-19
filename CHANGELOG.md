CHANGELOG
=========

すべての注目すべき変更は、このファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
-------------------

初回公開リリース。日本株自動売買システム "KabuSys" の基盤機能を追加しました。

Added
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) を追加。バージョンは 0.1.0。
  - モジュール群を公開: data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探すため CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env 行パーサーは export KEY=val、クォート（', "）、インラインコメント等に対応。
  - 必須環境変数取得用 _require() と Settings クラスを提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス (DUCKDB_PATH, SQLITE_PATH)
    - 実行環境判定 (KABUSYS_ENV: development/paper_trading/live) と LOG_LEVEL バリデーション
    - is_live / is_paper / is_dev ユーティリティ

- データ取得／保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
    - リトライ（指数バックオフ、最大 3 回）を実装。対象はタイムアウト・408/429/5xx 等。
    - 401 時はトークンを自動リフレッシュして 1 回リトライ（再帰防止フラグあり）。
    - ページネーション対応で /prices/daily_quotes, /fins/statements, /markets/trading_calendar を取得。
    - 取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への保存関数（冪等性）
    - save_daily_quotes: raw_prices への保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials への保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar への保存（ON CONFLICT DO UPDATE）。
    - 全保存で fetched_at を UTC で記録し、重複を上書きする実装。
  - 入出力処理ユーティリティ
    - _to_float / _to_int: 変換ルールを厳密に扱い、不正値は None にする。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集・前処理・DB 保存パイプラインを実装。
    - デフォルトソースに Yahoo Finance のカテゴリ RSS を含む。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）を削除、クエリソート、フラグメント削除。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化。
    - RSS 取得は defusedxml を利用して XML 関連の脆弱性を軽減。gzip 解凍とレスポンスサイズ上限（10MB）チェックを実装。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストを検証するカスタムリダイレクトハンドラ。
      - ホストがプライベート/ループバック/リンクローカルであれば接続を拒否。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を用いて新規挿入された記事 ID を返す（チャンク/トランザクション処理）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをバルク挿入（ON CONFLICT DO NOTHING、チャンク処理、トランザクション）。
    - 銘柄コード抽出: 正規表現で4桁数字を抽出し、与えられた known_codes セットでフィルタ（重複除去）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema に基づくスキーマ定義と初期化モジュールを追加（3 層: Raw / Processed / Feature / Execution 層を想定）。
  - Raw 層の DDL を実装（raw_prices, raw_financials, raw_news, raw_executions の定義開始）。
  - 各テーブルの型制約・PRIMARY KEY・CHECK を設定してデータ整合性を担保。

- 研究用モジュール (src/kabusys/research/)
  - feature_exploration.py
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）への将来リターンを一括 SQL で計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。無効レコード除外、有効レコードが3未満なら None を返す。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸め誤差対策として round(v,12) を適用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。データ不足時は None。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御やカウント閾値を実装。
    - calc_value: raw_financials から最新報告（target_date 以前）を取得して PER/ROE を計算。
    - ファクター計算はいずれも DuckDB 接続と prices_daily/raw_financials テーブルのみを参照（外部 API へアクセスしない）。
  - research パッケージ __init__ で主要関数群を再公開（zscore_normalize を含む）。

Performance / Reliability
- API 呼び出しのレート制限、ページネーション、トークンキャッシュ、リトライ／バックオフを実装して取得の安定性を向上。
- ニュース保存・銘柄紐付けはチャンク単位のバルク INSERT / 単一トランザクションで実行し、DB オーバーヘッドを低減。
- 保存操作は冪等性（ON CONFLICT）を保証。

Security
- ニュース収集で SSRF 対策を導入（スキーム検証、プライベートホスト検出、リダイレクト検査）。
- defusedxml を用いた XML パースで XML 関連攻撃を軽減。
- 外部からの大規模レスポンス（Gzip含む）に対してサイズ上限を設けてメモリ DoS を防止。

Notes / Limitations
- strategy/ execution の実装はこのバージョンでは空のパッケージ（プレースホルダ）。
- DuckDB のスキーマ定義ファイルは Raw 層の DDL を中心に実装。Feature / Processed 層の完全な DDL は今後追加予定。
- 外部依存（pandas など）は極力避け、研究モジュールは標準ライブラリ + duckdb のみで実装している。
- 一部のファイルは将来的に細かい例外処理やユニットテスト追加の余地あり。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

License
- （ソースにライセンス表記がないためここでは明記していません。リポジトリの LICENSE を参照してください）

---