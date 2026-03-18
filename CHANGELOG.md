# Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠しています。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名/バージョン定義（__version__ = "0.1.0"）および公開サブパッケージ一覧を追加。

- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
    - .env/.env.local の優先度制御（OS 環境変数保護、override ロジック）。
    - .env パーサー実装（export 構文対応、クォート・エスケープ・インラインコメントの扱いなど）。
    - Settings クラスを追加し、J-Quants トークン・kabu ステーションパスワード・Slack トークン・DB パス等のプロパティを提供。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。
    - Path 型での DB パス取得（duckdb/sqlite のデフォルトパス設定）。

- データ取得クライアント（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアント実装（ID トークン取得、ページネーション対応のデータ取得）。
    - レート制限対応（固定間隔スロットリング）とグローバル RateLimiter 実装（120 req/min に準拠）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）と 429 の Retry-After 優先処理。
    - 401 受信時のトークン自動リフレッシュ（1 回まで）とモジュールレベルのトークンキャッシュ共有。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応の取得関数を実装。
    - save_daily_quotes / save_financial_statements / save_market_calendar：DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、異常値や欠損値に安全に対処。
    - fetched_at に UTC ISO タイムスタンプを記録（Look-ahead bias の追跡を容易にする設計）。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードからのニュース収集パイプラインを実装。
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 対策）。
      - SSRF 防止のためスキーム検証（http/https のみ）・プライベートIP/ホストチェック・リダイレクト前検証（カスタム RedirectHandler）を実装。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - 許可されていないスキームや不正レスポンス時は安全にスキップ。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と SHA-256 ベースの記事 ID 生成（先頭32文字）による冪等性確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - fetch_rss: RSS パース→記事リスト作成（日時パースのフォールバックや content:encoded 優先）を実装。
    - DB 保存: save_raw_news（INSERT ... ON CONFLICT DO NOTHING + RETURNING を用い新規挿入のみIDを返す。チャンク/トランザクション処理）と save_news_symbols / _save_news_symbols_bulk（news_symbols への紐付けを効率的に保存）を実装。
    - 銘柄コード抽出 (extract_stock_codes): テキストから 4 桁銘柄コードを抽出し known_codes に基づきフィルタ。重複除去。

- 研究・特徴量モジュール
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: DuckDB の prices_daily を参照して指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。SQL の LEAD を用いた一括取得、対象欠損時は None を返す仕様。
    - calc_ic: ファクターと将来リターンを code で結合し Spearman（ランク相関）を計算。有効レコード数が 3 未満の場合は None を返す。ties は平均ランクで処理。
    - rank: 同順位は平均ランクにするランク関数（丸めで浮動小数の ties 検出漏れを防止）。
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）を計算。None/非有限値を除外。
  - src/kabusys/research/factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を計算（WINDOW 関数、必要データ不足時は None）。
    - calc_volatility: atr_20（ATR の単純平均）、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播を正しく扱う実装）。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER/ROE を計算（EPS=0/欠損時の扱いは None）。ROW_NUMBER を用いた最新財務レコード抽出。
  - src/kabusys/research/__init__.py:
    - 主要関数群をパッケージ公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）および zscore_normalize の再エクスポート。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py:
    - DataLayer（Raw/Processed/Feature/Execution）設計に基づくテーブル定義群を追加。
    - raw_prices, raw_financials, raw_news, raw_executions（部分定義）などの DDL を定義。
    - 各テーブルに主キーや型チェック（CHECK）を付与しデータ整合性を確保。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- ニュース収集モジュールに対する SSRF 対策、XML パースの安全化、レスポンスサイズ制限を追加。
- J-Quants クライアントはトークンの自動リフレッシュとリトライ設計により認証失敗や一時的なネットワーク障害に耐性を持たせている。

### 既知の制限・注意事項 (Notes)
- research モジュールは DuckDB の prices_daily / raw_financials テーブルのみを参照する設計で、実際のデータ投入は別途スクリプトや ETL によって行う必要があります。
- data.stats の zscore_normalize は別モジュール（kabusys.data.stats）で提供される前提です（本差分に実装コードは含まれていません）。
- schema.py の raw_executions 定義はファイル末尾で途中になっているため、追加の実装が必要です。
- 一部のサブパッケージ（execution, strategy）に対する __init__.py がプレースホルダとして存在します（今後の実装予定）。

もしリリースノートに含めたい追加情報（貢献者、リリース手順、マイグレーション手順など）があれば教えてください。必要に応じて追記します。