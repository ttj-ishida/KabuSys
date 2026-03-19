# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全バージョンはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-19

初回リリース。

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージメタ情報: `src/kabusys/__init__.py` に `__version__ = "0.1.0"` と公開モジュール一覧 (`__all__`) を定義。

- 環境設定管理
  - `src/kabusys/config.py`
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して自動で `.env` / `.env.local` を読み込む機能を実装（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` パーサーは `export KEY=val`、クォート文字列やインラインコメントの扱いに対応。
    - 必須環境変数取得のヘルパ `_require()` と、`Settings` クラス（J-Quants / kabu / Slack / DB / システム設定）のプロパティを提供。
    - `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の入力検証を実装。
    - デフォルト値: `KABU_API_BASE_URL`、`DUCKDB_PATH`（data/kabusys.duckdb）、`SQLITE_PATH`（data/monitoring.db）。

- データ層（DuckDB）関連
  - `src/kabusys/data/schema.py`
    - Raw 層のテーブル定義（raw_prices、raw_financials、raw_news、raw_executions など）を DDL で定義・初期化できるモジュールを追加（DataSchema.md に準拠した設計）。
    - スキーマは主キー制約やチェック制約を含む。

- J-Quants API クライアント
  - `src/kabusys/data/jquants_client.py`
    - API 呼び出しユーティリティ `_request()` を実装。機能:
      - API レート制御（120 req/min 固定間隔スロットリング）を `_RateLimiter` で実装。
      - リトライ（指数バックオフ、最大 3 回）とステータスコードによる再試行制御（408/429/5xx 対応）。
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュを実装。
      - ページネーション対応の取得関数 `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
    - DuckDB への冪等保存関数を追加:
      - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` は `ON CONFLICT DO UPDATE` により重複更新を行い冪等性を保証。
    - データ整形ユーティリティ `_to_float`, `_to_int` を実装し、不正値や空値を安全に扱う。

- ニュース収集モジュール
  - `src/kabusys/data/news_collector.py`
    - RSS フィードから記事を収集し `raw_news` に保存する一連の機能を実装。
    - セキュリティ・堅牢性機能:
      - defusedxml を用いた XML パース（XML Bomb 対策）。
      - SSRF 対策: リダイレクト時にスキーム検証・ホストのプライベートアドレス検査を行う `_SSRFBlockRedirectHandler`、初期 URL のプライベート検査。
      - 許可スキームは http/https のみ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - トラッキングパラメータ（utm_*, fbclid 等）を除去する URL 正規化。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - データ保存:
      - `save_raw_news` はチャンク挿入とトランザクションを使用し、INSERT ... RETURNING で実際に挿入された記事 ID を返す。
      - `save_news_symbols` / `_save_news_symbols_bulk` は記事と銘柄の紐付けを一括保存（ON CONFLICT DO NOTHING）し、挿入数を正確に返す。
    - 銘柄抽出機能 `extract_stock_codes` を実装（4桁数字の検出と既知コードフィルタリング）。

- リサーチ（ファクター計算・探索）
  - `src/kabusys/research/factor_research.py`
    - 戦略用定量ファクター（Momentum / Volatility / Value / Liquidity）の計算関数を実装:
      - `calc_momentum`: 1M/3M/6M リターン、MA200 乖離率。データ不足時に None を返す設計。
      - `calc_volatility`: ATR20、相対ATR、20日平均売買代金、出来高比率。
      - `calc_value`: EPS/ROE に基づく PER/ROE の算出（raw_financials から直近財務を取得）。
    - DuckDB の SQL ウィンドウ関数を活用して効率的に計算。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応、1クエリ取得）。
    - ランク相関（Spearman）による IC 計算 `calc_ic`（ランク変換・ties の平均ランク処理を含む）。
    - `rank` ユーティリティ（同順位は平均ランク、丸めによる ties 検出対策あり）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - 設計方針として外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装。
  - `src/kabusys/research/__init__.py` で上記主要関数と zscore_normalize（データ層のユーティリティ）を再エクスポート。

- モジュールのプレースホルダ
  - `src/kabusys/execution/__init__.py`、`src/kabusys/strategy/__init__.py` を追加（将来的な機能のための名前空間を用意）。

### 変更 (Changed)
- （該当なし）初回リリースのため変更履歴はありません。

### 修正 (Fixed)
- （該当なし）初回リリースのため修正履歴はありません。

### セキュリティ (Security)
- RSS 処理で SSRF 対策を導入（スキーム・リダイレクト先スキャン・プライベート IP 拒否）。
- XML パースに defusedxml を利用して XML ベースの攻撃を軽減。
- ニュース取得の際に受信サイズ制限・gzip 解凍後の検査を実装。

### 既知の制限 / 注意事項 (Notes)
- Research モジュールは外部ライブラリ（pandas, numpy 等）に依存しない設計のため、大規模データ処理の最適化や機能拡張は今後の課題。
- `strategy` や `execution` 名前空間は存在するが、現バージョンでは実装が含まれていない（プレースホルダ）。
- J-Quants API クライアントは ID トークンを内部キャッシュして再利用する設計。長時間のバッチ処理等でトークン寿命に注意。
- DuckDB テーブル定義は Raw 層を中心に実装済み。運用前に schema 初期化手順（DDL 実行）を実行してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが不足すると `Settings` のプロパティアクセスで ValueError が発生します。

今後の予定（例）
- Execution / Strategy の実装（発注ロジック・ポジション管理）
- Feature 層・Processed 層の追加 DDL と ETL 実装
- パフォーマンス最適化（大規模データ向けのバッチ処理、高速集計）

---

（注）この CHANGELOG は現行コードベースの実装内容から推測して作成しています。実際の変更履歴や設計意図と差異がある場合があります。