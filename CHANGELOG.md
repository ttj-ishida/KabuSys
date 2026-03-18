# Changelog

すべての重要な変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

現在のバージョン: 0.1.0 (2026-03-18)

## [0.1.0] - 2026-03-18

### 追加 (Added)
- 基本パッケージ構成
  - src/kabusys/__init__.py によりパッケージのバージョンとエクスポートを定義（__version__ = 0.1.0、data/strategy/execution/monitoring を公開）。
- 環境設定/ロード機能
  - src/kabusys/config.py
    - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - .env パーサ実装: export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - 既存 OS 環境変数を保護する protected 機構、.env.local による上書き優先順位。
    - Settings クラス: J-Quants / kabu API / Slack / DB パス等のプロパティ、KABUSYS_ENV と LOG_LEVEL の検証、便利な is_live/is_paper/is_dev フラグ。
- データ取得/保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py
    - API 呼び出しユーティリティ（_request）を実装：JSON デコード検証、ページネーション対応、最大 3 回のリトライ（指数バックオフ）、408/429/5xx に対する再試行ロジック。
    - 401（Unauthorized）受信時の自動トークンリフレッシュ（1回のみ）機能。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 等の取得関数（ページネーション対応、取得件数ログ出力）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保し、PK 欠損行のスキップや saved 件数のログ出力を行う。
    - 型変換ユーティリティ (_to_float, _to_int) を用意し、不正データに対して安全に None を返す設計。
- ニュース収集（RSS → DuckDB）
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と記事解析（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - セキュリティ強化:
      - defusedxml による XML パース（XML Bomb 等対策）
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト時の事前検査、ホストのプライベート/ループバック判定
      - 応答サイズ制限（MAX_RESPONSE_BYTES、ガードして超過時は棄却）
      - gzip 解凍後サイズチェック（Gzip bomb 対策）
    - 冪等性と効率化:
      - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成（トラッキングパラメータ除去）。
      - INSERT ... ON CONFLICT DO NOTHING と RETURNING を利用して実際に挿入された記事IDを返す（save_raw_news）。
      - 銘柄紐付けは重複排除・チャンク分割・1トランザクションでバルク挿入（_save_news_symbols_bulk）。
    - 前処理ユーティリティ:
      - URL 正規化（tracking パラメータ削除、クエリソート、フラグメント削除）
      - テキスト前処理（URL 除去・空白正規化）
      - RSS pubDate の堅牢なパース（UTC 正規化、失敗時は現在時刻で代替）
      - 銘柄コード抽出（4 桁数字の候補から known_codes フィルタ）
- DuckDB スキーマ定義と初期化（Raw Layer）
  - src/kabusys/data/schema.py
    - raw_prices, raw_financials, raw_news, raw_executions 等の DDL 定義（CREATE TABLE IF NOT EXISTS）。
    - 各カラムに対する型・制約（CHECK / PRIMARY KEY）を明示し、Raw Layer の基盤を提供。
- リサーチ用特徴量・統計モジュール
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)：LEAD を使った一括取得、ホライズン指定（デフォルト [1,5,21]）、データ不足時は None。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman ρ（ランク相関）を実装、データの欠損・非有限値を排除、レコード数が少ない場合は None。
    - rank：同順位は平均ランクで処理、浮動小数点誤差対策として round(..., 12) を使用。
    - factor_summary：count/mean/std/min/max/median を計算（None は除外）。
  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）：1m/3m/6m リターン、MA200 乖離率。必要行数不足時は None。
    - ボラティリティ/流動性（calc_volatility）：20 日 ATR（true range の扱いに注意）、ATR の相対値（atr_pct）、20 日平均売買代金・出来高比率を計算。NULL 伝播を正しく扱う設計。
    - バリュー（calc_value）：raw_financials から target_date 以前の最新財務を取得し PER / ROE を計算。EPS が 0/欠損の場合は PER を None とする。
  - src/kabusys/research/__init__.py により主要関数をエクスポート（zscore_normalize を含む）。
- 軽量なパッケージ API 用の空の __init__ モジュールを戦略/実行モジュールに配置
  - src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py（将来的な拡張用のプレースホルダ）。

### 改善 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### セキュリティ (Security)
- news_collector にて複数の SSRF / XML 攻撃対策を実装（_SSRFBlockRedirectHandler、_is_private_host、defusedxml、応答サイズ制限等）。
- J-Quants クライアントは認証トークン管理と自動リフレッシュを実装し、不正な 401 応答を適切に処理。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

---

注記 / 実装上の設計方針（抜粋）
- Research モジュールは本番発注 API にアクセスしない方針（prices_daily / raw_financials のみ参照）。
- 外部ライブラリへの依存を最小化する設計（research の一部は標準ライブラリのみで実装）。
- DuckDB を内部データレイヤ（Raw / Processed / Feature / Execution）として利用する前提。
- DB への書き込みはできるだけ冪等に（ON CONFLICT）し、実際に追加した件数が取得できるようにしている。

今後の予定（例）
- Execution/Strategy 層の具体実装（発注ロジック、ポジション管理、モニタリング）
- Feature Layer の追加ファクターや zscore_normalize の拡張
- テストカバレッジの拡充と CI/CD の整備

---