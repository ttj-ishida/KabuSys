# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成しています。

## [0.1.0] - 2026-03-19
初回リリース（初期実装）。

### 追加
- パッケージ基盤
  - パッケージ情報: kabusys v0.1.0 を追加（src/kabusys/__init__.py）。
  - モジュール分割: data, strategy, execution, research, monitoring 等の名前空間を想定した構成を導入。

- 設定・環境読み込み（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にプロジェクトルートを探索し、自動的に .env/.env.local を読み込む。
  - .env パーサ実装: export 形式の対応、クォート/エスケープ、インラインコメント処理などを細かく処理。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを抑制可能。
  - 必須設定の取得時に _require による ValueError 投げる仕組みを提供。
  - 設定例（必須環境変数）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
  - DB パス設定（既定値）: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションを実装（許容値の定義あり）。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装:
    - 固定間隔の RateLimiter（120 req/min）でレート制限を厳守。
    - 再試行ロジック（指数バックオフ、最大3回）を実装。対象ステータス（408, 429, 5xx）への対応。
    - 401 受信時はトークンを自動でリフレッシュして 1 回リトライ（無限再帰防止）。
    - ページネーション対応で fetch_daily_quotes / fetch_financial_statements を実装。
    - JPX マーケットカレンダー取得 fetch_market_calendar 実装。
    - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を提供し、ON CONFLICT DO UPDATE による冪等性を確保。
    - 型変換ユーティリティ: _to_float, _to_int（文字列/浮動小数点対応、無効値は None）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集ライブラリ実装:
    - RSS フェッチ fetch_rss、XML の安全パース（defusedxml）対応。
    - SSRF 対策: URL スキーム検証、リダイレクト時のスキーム/ホスト検査、プライベートIP/ループバックの拒否。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 展開後のサイズ検査（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去(_normalize_url)、記事ID は正規化 URL の SHA-256（先頭32文字）。
    - テキスト前処理（URL 除去・空白正規化）。
    - raw_news テーブルへの冪等保存（save_raw_news）および挿入済み ID の返却（INSERT ... RETURNING を利用）。
    - 銘柄コード抽出（4桁数字）と一括紐付け保存（save_news_symbols / _save_news_symbols_bulk）。
    - run_news_collection: 複数ソースを順次処理し、ソース単位で失敗を隔離して継続するジョブ実装。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw layer 用の DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（スキーマ・制約を含む）。
  - 初期化/DDL 管理を想定したモジュール化。

- リサーチ（特徴量・ファクター計算）モジュール（src/kabusys/research）
  - feature_exploration.py:
    - calc_forward_returns: 指定日の終値を基準に複数ホライズンの将来リターンを一括取得する関数。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。未経由/非有限値の除外、レコード不足時は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク化ユーティリティ（丸めにより ties 検出を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー。
    - 設計上、DuckDB の prices_daily テーブルのみ参照し、本番口座や発注 API にはアクセスしない方針。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20（20日 ATR）、atr_pct（相対 ATR）、avg_turnover（20日平均売買代金）、volume_ratio を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS=0 や欠損時は None）。
    - 全関数は DuckDB の prices_daily/raw_financials のみ参照。外部ライブラリ（pandas 等）に依存しない実装。

- research パッケージのエクスポート（src/kabusys/research/__init__.py）
  - 主なユーティリティ関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

### 変更
- （初版のため履歴的な「変更」は無し。全て新規追加）

### 修正
- （初版のため既知のバグ修正履歴は無し）

### 既知の注意点 / 移行メモ
- 自動で .env をプロジェクトルートから読み込みますが、CI/テスト環境などでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化してください。
- 必須の環境変数が未設定の場合、Settings のアクセサで ValueError が発生します（例: settings.jquants_refresh_token）。
- J-Quants クライアントは内部でトークンキャッシュを保持します。トークンの強制更新が必要な場合は get_id_token を明示的に呼ぶことが可能です。
- DuckDB テーブル名や列の制約（CHECK / PRIMARY KEY）が厳密に定義されています。不正なデータを INSERT するとエラーになりますので、保存関数は事前にデータ整形・型変換を行います。
- ニュース収集は defusedxml と SSRF/サイズチェックなど多層の防御を行っていますが、外部フィードの多様性によるパース失敗はあり得ます（その場合はログ出力してスキップ）。

### セキュリティ
- ニュース収集:
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を軽減。
  - リダイレクト前後にスキームとホスト検証を行い、プライベートIP/ループバック/IPマルチキャスト等へのアクセスを拒否（SSRF 対策）。
  - レスポンスサイズ上限・gzip 解凍後の上限チェックで DoS / Gzip Bomb 対策を実施。
- J-Quants クライアント:
  - 認証トークンの自動リフレッシュは allow_refresh フラグで制御し、無限再帰を回避。
  - レート制限と再試行ロジックにより API の健全性を保護。

もし追加で「リリース日を変更したい」「各ファイルごとの細かい差分注釈を含めたい」「英語版 CHANGELOG を併記したい」等の要望があれば教えてください。