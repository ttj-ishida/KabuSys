# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトの初回リリースはバージョン 0.1.0 です。

## [0.1.0] - 2026-03-18

初期リリース。日本株自動売買システム「KabuSys」のコアモジュールを実装。

### 追加 (Added)

- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - モジュール分割: data, strategy, execution, monitoring の公開（__all__）。

- 環境設定/初期化 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を安全に読み込む機能を実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索して自動で .env/.env.local を読み込み）。
  - .env パーサの強化:
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント処理（クォートの有無により動作を分離）。
  - 自動ロード無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) を追加。
  - 必須キー取得のヘルパー (_require) と Settings クラスを実装（J-Quants / kabuAPI / Slack / DB パス / 環境種別 / ログレベル等）。
  - KABUSYS_ENV・LOG_LEVEL のバリデーションとユーティリティプロパティ（is_live / is_paper / is_dev）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 日足（OHLCV）、財務データ（四半期）、マーケットカレンダーを取得する fetch_* 関数群。
    - ページネーション対応。
  - 認証処理: リフレッシュトークンから ID トークンを取得する get_id_token を実装。
  - レート制限管理: 固定間隔スロットリング _RateLimiter（120 req/min 相当）。
  - 再試行ロジック: 指数バックオフ付きリトライ（最大 3 回）、HTTP 429/408/5xx を対象。
  - 401 時の自動トークンリフレッシュと安全な再試行制御（無限再帰防止）。
  - DuckDB への永続化ユーティリティ:
    - save_daily_quotes: raw_prices へ冪等保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials へ冪等保存。
    - save_market_calendar: market_calendar へ冪等保存。
  - 変換ユーティリティ _to_float / _to_int を実装（型安全なパース・不正値を None にする挙動）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する機能群を実装。
    - fetch_rss: RSS 取得、XML パース、記事整形（title/content の前処理）を行う。
    - save_raw_news: INSERT ... RETURNING を用いた冪等保存（チャンク挿入、トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存。
    - run_news_collection: 複数ソースを順次取得して DB に保存する統合ジョブ。
  - セキュリティ・健全性対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト先のスキーム/ホスト検査、プライベート IP 判定（DNS 解決を含む）、_SSRFBlockRedirectHandler。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip データの二重チェック（解凍後も上限検査）。
    - トラッキングパラメータ除去・URL 正規化（_normalize_url）と、記事ID を SHA-256 の先頭 32 文字で生成（_make_article_id）。
    - 記事本文の前処理（URL 除去、空白正規化）。
  - 銘柄抽出ユーティリティ extract_stock_codes（4 桁銘柄コード抽出、重複除去、既知銘柄フィルタリング）。
  - デフォルト RSS ソース定義（yahoo_finance）。

- DuckDB スキーマ初期化 (kabusys.data.schema)
  - DataSchema に基づくテーブル DDL を追加（raw_prices / raw_financials / raw_news / raw_executions 等の定義を含む）。
  - 型チェック制約や PRIMARY KEY、DEFAULT を定義してデータ品質を担保。

- リサーチ/ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを DuckDB 上で一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（ties の扱い、最小レコード数チェック）。
    - rank: ランク計算（同順位は平均ランク、丸め処理で ties 検出誤差を抑制）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - 実装ポリシー: pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（真の true_range の NULL 伝播制御、window カウント検査）。
    - calc_value: raw_financials と prices_daily を結合して PER/ROE を算出（最新の財務レコード取得ロジックを含む）。
    - スキャン範囲・ウィンドウ日数やバッファ計算を明示してパフォーマンスを配慮。
  - research パッケージ __init__ で主要関数を公開（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

### 変更 (Changed)

- なし（初回リリースのため該当なし）。

### 修正 (Fixed)

- なし（初回リリースのため該当なし）。

### セキュリティ (Security)

- RSS パーサと HTTP クライアント周りに以下の対策を実装:
  - defusedxml による XML パースで XML 攻撃を軽減。
  - SSRF 対策: リダイレクト時のスキーム/ホスト検査、プライベート IP の拒否、最終 URL 再検証。
  - レスポンスサイズ制限と gzip 解凍後の再チェックでメモリ DoS を軽減。
  - URL スキーム制限（http/https のみ）で file:// 等の不正スキームを排除。

### 注意事項 / 既知の制限 (Notes)

- research モジュールの設計哲学として「DuckDB の prices_daily / raw_financials のみ参照し、発注 API にはアクセスしない」ことを明示。これにより look-ahead bias を防止する設計になっています。
- calc_* 系関数は営業日ベースの「連続レコード数」を想定しており、カレンダー日の扱いを内部で補正するため、prices_daily に連続的な営業日データが必要です。
- J-Quants クライアントは urllib を使用した実装であり、外部 HTTP ライブラリ（requests 等）に依存しない設計です。
- 一部のユーティリティ（例: kabusys.data.stats.zscore_normalize）は本一覧に含まれるファイル外で実装されている想定です。

--- 

今後のリリースでは、発注・実行 (execution) および戦略 (strategy) の具体的な実装、監視・アラート機能、テストカバレッジ改善や CLI/運用ドキュメントの追加などを予定しています。