# CHANGELOG

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。
リリースはセマンティックバージョニングに従います。

## [Unreleased]

---

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主に以下の機能・モジュールを含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) とバージョン定義 (`__version__ = "0.1.0"`)。
  - モジュール公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック（.git / pyproject.toml を探索）により CWD に依存しない自動読み込みを実現。
  - .env/.env.local 読み込み順序と override 挙動（OS 環境変数保護）を実装。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - 必須設定の取得メソッド（存在しない場合は ValueError）:
    - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
  - その他設定:
    - `KABUSYS_ENV`（development / paper_trading / live、検証付き）
    - `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL、検証付き）
    - DB パスデフォルト: `DUCKDB_PATH="data/kabusys.duckdb"`, `SQLITE_PATH="data/monitoring.db"`

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からの日足・財務データ・マーケットカレンダー取得関数を実装（ページネーション対応）。
  - レートリミッタ（120 req/min 固定間隔スロットリング）を実装。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。
  - 401 発生時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを実装（再帰回避）。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - DuckDB への冪等保存関数:
    - `save_daily_quotes` → raw_prices テーブルに ON CONFLICT DO UPDATE を使用して保存。
    - `save_financial_statements` → raw_financials テーブルに冪等保存。
    - `save_market_calendar` → market_calendar テーブルに冪等保存。
  - 入力変換ユーティリティ `_to_float`, `_to_int` 実装（堅牢な型変換）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集、前処理、DuckDB への冪等保存ワークフローを実装。
  - 正規化・安全対策:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - defusedxml を用いた XML パースで XML Bomb 等に対処。
    - SSRF 対策: リダイレクト先のスキーム検査とホストのプライベートアドレス検査（`_is_private_host`）。
    - レスポンスサイズ上限（10MB）と gzip 解凍後の検査（Gzip bomb 対策）。
    - 受信ヘッダの Content-Length 検査。
  - DB 保存:
    - `save_raw_news`: INSERT ... RETURNING を使い、実際に挿入された記事 ID を返す（チャンク分割、トランザクション）。
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄の紐付けを冪等に保存（INSERT ... RETURNING）。
  - 銘柄コード抽出ロジック（正規表現で 4 桁数字を抽出し known_codes フィルタ適用）。
  - RSS 取得ユーティリティ `fetch_rss`、統合ジョブ `run_news_collection` を提供（ソースごとに独立してエラーハンドリング）。

- リサーチ（特徴量・ファクター計算） (src/kabusys/research/)
  - feature_exploration.py
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応、一括 SQL 取得）。
    - スピアマンランク相関（IC）計算 `calc_ic`（rank 関数含む、ties の平均ランク処理）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリで実装。
  - factor_research.py
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）といった定量ファクターを DuckDB 上の SQL ウィンドウ関数で計算する関数を実装。
    - データ不足時に None を返す等、欠損処理に配慮。
    - スキャン範囲にカレンダーバッファを設けて週末/祝日を吸収する設計。
  - research パッケージ初期化で主要関数をエクスポート（zscore_normalize を含む）。

- データベーススキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用の DDL スクリプトを追加（Raw / Processed / Feature / Execution 層の定義に準拠）。
  - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（CHECK 制約や PRIMARY KEY を含む）。

- テスト・差し替え用のフック
  - news_collector の `_urlopen` はテスト時にモック可能（SSRF ハンドラ付オープナーを差し替えられる）。

### 変更点 (Changed)
- N/A（初回リリース）

### 修正 (Fixed)
- N/A（初回リリース）

### セキュリティ (Security)
- RSS フィード取得において複数の SSRF 対策を実施：
  - リダイレクト先のスキーム検証、プライベートアドレス検査（DNS 解決を含む）。
  - defusedxml を使用して XML パースの安全性を確保。
  - レスポンスサイズ制限（10MB）と gzip 解凍後の検査を導入し、リソース枯渇攻撃や Gzip bomb を軽減。

### 互換性の注意 (Migration / Compatibility)
- DuckDB に依存するコードが多数あるため、実行環境に DuckDB をインストールする必要があります。
- J-Quants API の認証には `JQUANTS_REFRESH_TOKEN` が必須です（環境変数、または .env に設定してください）。
- 自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後や環境によっては `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効にすることができます。
- research モジュールは pandas 等の外部データ処理ライブラリに依存しない設計です（軽量だが性能上のトレードオフがある可能性あり）。

### 既知の制約 / 備考 (Notes)
- 外部依存:
  - defusedxml（XML パースの安全化）を使用。
  - duckdb が必須（DB 接続型の引数を多用）。
  - ネットワーク実装は標準ライブラリの urllib を利用（requests は不要）。
- news_collector の URL 正規化で除去されるトラッキングパラメータプレフィックスは `_TRACKING_PARAM_PREFIXES` に定義（utm_ 等）。
- jquants_client のレートリミットは固定間隔（スロットリング）方式を採用。厳密なトラフィック管理が必要な場合は実運用での監視を推奨。
- 一部テーブル定義（raw_executions 等）はスニペットの都合で途中までの定義が含まれます。実運用前に schema モジュール全体を確認してください。

---

（今後のリリースでは、変更点を Breaking Changes / Added / Changed / Fixed / Security の各セクションに分けて記載します。）