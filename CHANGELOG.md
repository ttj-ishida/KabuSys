# CHANGELOG

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
各リリースは下位互換性のある変更・機能追加・バグ修正・セキュリティ関連などをカテゴリ別にまとめています。

## [Unreleased]
- 今後のリリースで予定の変更点や追加予定の機能をここに記載します。

## [0.1.0] - 2026-03-19
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成を実装。バージョンは 0.1.0。
  - サブパッケージのエクスポート設定: data, strategy, execution, monitoring。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準に探索）。
  - .env のパース機能を実装（export プレフィックス、クォート、インラインコメント、エスケープ対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 設定取得用 Settings クラスを提供（J-Quants トークン、kabu API、Slack、DBパス、実行環境/ログレベルの検証を含む）。
  - 環境変数バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- Data モジュール
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - HTTP リクエストの共通処理を実装（ページネーション対応）。
    - リトライ処理（指数バックオフ、最大 3 回）および 401 受信時の自動トークンリフレッシュに対応。
    - データ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数を実装: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - 型変換ユーティリティ(_to_float/_to_int)を実装して不正な入力を安全に扱う。

  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィードの取得・パースと記事整形の実装（fetch_rss, preprocess_text）。
    - defusedxml を利用した堅牢な XML パース（XML Bomb 対策）。
    - Gzip 圧縮対応とレスポンスサイズ上限チェック（MAX_RESPONSE_BYTES）。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - SSRF 対策:
      - 事前にホストのプライベートIP判定を実施（_is_private_host）。
      - リダイレクト時にスキーム/ホストを検査する専用ハンドラを導入。
      - http/https スキーム以外の URL を拒否。
    - DuckDB への保存関数:
      - save_raw_news: INSERT ... RETURNING を用いたチャンク挿入（トランザクション内でコミット／ロールバック）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存。
    - 銘柄コード抽出ユーティリティ (extract_stock_codes): テキストから 4 桁銘柄コードを抽出し known_codes と照合。

  - スキーマ定義 (src/kabusys/data/schema.py)
    - DuckDB 用のDDLを定義（Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions 等）。
    - テーブル定義に制約（PRIMARY KEY, CHECK 制約、NOT NULL 等）を含む。

- Research モジュール
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns)：DuckDB の prices_daily を参照し、指定ホライズンのリターンを一括で取得。
    - IC（Information Coefficient）計算 (calc_ic)：ファクターと将来リターンの Spearman ランク相関を実装（ties の平均ランク処理を含む）。
    - ランク付けユーティリティ (rank) とファクター統計サマリ (factor_summary) を実装。
    - 標準ライブラリのみでの実装を志向。

  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム (calc_momentum)：1M/3M/6M リターンおよび 200 日移動平均乖離率（MA200）を計算。
    - ボラティリティ/流動性 (calc_volatility)：20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー (calc_value)：raw_financials から最新財務データを取得して PER, ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、本番発注 API 等にはアクセスしない設計。

- いくつかのユーティリティ
  - zscore_normalize（kabusys.data.stats からエクスポートされる想定）を research パッケージの公開 API に含める。

### 変更 (Changed)
- なし（初回リリースのため特段の変更履歴はなし）。

### 修正 (Fixed)
- なし（初回リリースのため既存バグ修正履歴はなし）。

### セキュリティ (Security)
- ニュース収集において以下の対策を導入:
  - defusedxml による XML パースで XML 関連攻撃を低減。
  - SSRF 対策（リダイレクト検査、プライベートIPチェック、スキーム検証）。
  - レスポンスサイズ上限の設定でメモリ DoS に対処。

---

注記:
- コードベースの説明に基づき推測してまとめています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。