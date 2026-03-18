# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-18

初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ全体
  - パッケージエントリポイントを追加 (src/kabusys/__init__.py)。バージョンは 0.1.0。
  - モジュール群を分割: data, strategy, execution, monitoring, research などの名前空間を準備。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env 自動ロード機能（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を独自実装（コメント、export プレフィックス、クォートエスケープ、インラインコメントの取扱い等に対応）。
  - 必須環境変数の取得ヘルパー _require と、KABUSYS_ENV / LOG_LEVEL の検証（許可値チェック）。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）や Slack / kabu API / J-Quants のトークン設定プロパティを提供。

- データレイヤ - J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からの日足・財務データ・マーケットカレンダー取得機能を追加（ページネーション対応）。
  - API 呼び出し共通処理:
    - 固定間隔スロットリングによるレート制限実装（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 受信時はリフレッシュトークンで ID トークンを自動更新して 1 回再試行。
    - JSON デコードエラーハンドリング。
    - ページネーション中のトークン共有のためのモジュールレベルキャッシュ。
  - DuckDB への冪等保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE を利用し重複を回避。
    - 値変換ヘルパー _to_float / _to_int を実装（不正値時は None を返す、int 変換で小数部がある場合は None などの挙動定義）。

- データレイヤ - ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード取得と raw_news/raw_symbols への保存パイプラインを実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクトの事前検証、ホストのプライベートアドレス判定、許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_* 等）を除去する URL 正規化と、正規化 URL の SHA-256（先頭32文字）で記事 ID を生成する冪等性。
    - _SSRFBlockRedirectHandler によるリダイレクト時の検証。
  - DB 保存:
    - save_raw_news: チャンク分割 + INSERT ... RETURNING による新規挿入 ID 取得。トランザクションでまとめて実行。例外時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括挿入（重複を除去、ON CONFLICT DO NOTHING を使用）。
  - テキスト前処理（URL除去、空白正規化）と RSS pubDate のパースヘルパーを実装。
  - 記事本文から銘柄コード（4桁）を抽出する extract_stock_codes を実装（known_codes によりフィルタリング）。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - feature_exploration.py:
    - calc_forward_returns: 指定日から将来リターン（複数ホライズン）を DuckDB 上で一括計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位を平均ランクとするランク化ユーティリティ（丸めで ties の検出漏れを防止）。
    - factor_summary: ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の NULL 伝播等に配慮）。
    - calc_value: raw_financials と prices_daily を結合して PER, ROE を計算（最新報告日ベース）。
  - research パッケージ初期エクスポートを実装（calc_momentum 等と zscore_normalize を公開）。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB のスキーマ DDL を定義（Raw Layer のテーブル定義を含む: raw_prices, raw_financials, raw_news, raw_executions ...）。
  - テーブルの制約（NOT NULL, PRIMARY KEY, CHECK 等）を明示。

### 変更 (Changed)
- n/a（初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- n/a（初回リリースのため修正履歴はありません）

### ドキュメント (Docs)
- 各モジュールに設計方針・処理フロー・使用上の注意を含むドキュメンテーション（モジュールドキストリング）を追加。設計上の注意点（本番 API へアクセスしない、Look-ahead Bias 対策など）を明示。

### セキュリティ (Security)
- RSS パーサに defusedxml を導入して XML 関連攻撃を軽減。
- ニュース収集での SSRF 対策、レスポンスサイズ上限、Gzip 解凍後のサイズ検査を実装。

### 既知の制約 / 注意点 (Known issues / Notes)
- DuckDB を利用するため duckdb パッケージが必要です。またニュース収集では defusedxml が必要です。
- research モジュール・data 保存処理は DuckDB 上の prices_daily/raw_financials/raw_prices 等のテーブルに依存します。これらのテーブルは適切に初期化・データ投入されていることを前提とします。
- calc_forward_returns の horizons は 1〜252 の整数に限定されます（252 を超えると ValueError）。
- RSS の pubDate パースで失敗した場合は警告ログを出し現在時刻 UTC を代替値として使用します（raw_news.datetime は NOT NULL）。
- 一部ファイル（例: schema.py の raw_executions 定義）はリストの途中までが掲載されています。完全なスキーマは実装済みの DDL をプロジェクト内で確認してください。

### 依存関係
- 主要依存: duckdb, defusedxml（XML パース用）。標準ライブラリの urllib, json, datetime などを多用。

---

今後の予定（例）
- execution 層（kabu ステーション API 経由の発注・約定管理）の実装。
- strategy 層の StrategyModel 実装および backtest/実運用連携。
- schema の追加テーブル（processed/feature/execution 層）の完成とマイグレーション機能。