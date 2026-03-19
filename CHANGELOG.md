# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、この CHANGELOG はコードベースから推測して作成した初期リリースのまとめです。

## [0.1.0] - 2026-03-19

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期化。モジュールエクスポート: data, strategy, execution, monitoring。バージョン: 0.1.0。

- 環境設定 / ロード機能
  - 環境変数読み込みユーティリティ（kabusys.config）。
    - .env / .env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない読み込み。
    - .env パーサ実装（export プレフィックス、引用符・エスケープ、インラインコメント対応）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパー _require。
    - 設定クラス Settings を提供（J-Quants / kabuAPI / Slack / DB パス / 環境判定 / ログレベル等）。

- データ取得・保存（J-Quants）
  - J-Quants API クライアント（kabusys.data.jquants_client）。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 冪等的な DuckDB 保存（raw_prices, raw_financials, market_calendar 向け ON CONFLICT ... DO UPDATE）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
    - 数値変換ユーティリティ（_to_float, _to_int）で不正値を安全に扱う。

- ニュース収集（RSS）
  - RSS ニュース収集モジュール（kabusys.data.news_collector）。
    - RSS フィード取得、XML パース、防御（defusedxml 使用）。
    - URL 正規化（tracking パラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 記事ID を正規化 URL の SHA-256（先頭32 文字）で生成し冪等性を確保。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキーム/プライベートアドレス検査（カスタム RedirectHandler）。
      - リモートホストがプライベート/ループバック/リンクローカル/マルチキャストかを検出して拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB、gzip 解凍後も検査）でメモリ DoS を軽減。
    - テキスト前処理（URL 除去・空白正規化）。
    - 銘柄コード抽出（本文から 4 桁コード抽出、known_codes によるフィルタ）。
    - DB 保存:
      - raw_news へのチャンク単位挿入（INSERT ... RETURNING で実際に挿入された ID を取得）。
      - news_symbols への紐付け保存（チャンク & 重複排除、RETURNING で挿入数を正確に返す）。
      - トランザクション制御（1 トランザクションでのチャンク挿入、例外時ロールバック）。

- リサーチ（特徴量・ファクター計算）
  - feature_exploration モジュール（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマン順位相関、欠損 / 非有限値処理、最小サンプル判定）。
    - ランク関数 rank（同順位は平均ランク、丸めによる ties 対応）。
    - ファクター統計要約 factor_summary（count/mean/std/min/max/median）。
    - 標準ライブラリのみでの実装（pandas 等非依存）。
  - factor_research モジュール（kabusys.research.factor_research）
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離、データ不足時は None）。
    - ボラティリティ calc_volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比）。
    - バリュー calc_value（raw_financials から最新財務を取得し PER/ROE を計算）。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照し外部 API にアクセスしない設計。
    - スキャン範囲バッファやウィンドウサイズ等の定数化による安定した参照範囲設定。

- スキーマ定義 / 初期化
  - DuckDB スキーマ定義モジュール（kabusys.data.schema）。
    - raw layer の DDL（raw_prices, raw_financials, raw_news, raw_executions などの定義）。
    - DataSchema.md に準拠した 3 層構造（Raw / Processed / Feature / Execution）の方針を記載。

- パッケージ再エクスポート
  - kabusys.research.__init__ で主要な計算ユーティリティを再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector:
  - defusedxml を利用して XML による攻撃（XML Bomb 等）への耐性を確保。
  - SSRF 対策を複数層で導入（URL スキーム制限、ホストのプライベート判定、リダイレクト時検査）。
  - レスポンスサイズと gzip 解凍後サイズの上限を設け、巨大レスポンスによる DoS を軽減。

### パフォーマンス (Performance)
- J-Quants クライアント:
  - レート制御を固定間隔（スロットリング）で実装し API 制限を安定して遵守。
  - ページネーションでトークンを共有し余計な認証コールを削減。
- news_collector / DB 保存:
  - INSERT をチャンク化して一括挿入し、トランザクション数と SQL オーバーヘッドを削減。
- リサーチ機能:
  - 複数ホライズンをまとめて 1 クエリで取得する等、DuckDB 上での処理効率化を意識した実装。

### 既知の制限 / 注意点 (Known issues / Notes)
- data/research モジュールは DuckDB の所定テーブル（prices_daily, raw_financials など）を前提としており、事前にスキーマ作成とデータ投入が必要。
- jquants_client の API ベース URL は内部定数 _BASE_URL を使用。認証トークンは settings.jquants_refresh_token に依存する。
- news_collector は既知銘柄コードのセット（known_codes）が与えられない場合は銘柄紐付けをスキップする。
- _to_int の挙動: "1.9" のような小数文字列は None を返す設計（意図しない切り捨てを防止）。

---

今後の予定（例）
- strategy / execution / monitoring の具体的実装（発注ロジック、ポジション管理、監視アラート等）。
- processed / feature layer の変換パイプライン実装。
- 単体テスト・統合テストの追加と CI 設定。

もし CHANGELOG に追記したい点（実際のコミット日や貢献者情報、リリースタグ等）があれば教えてください。必要に応じて日付や項目を修正します。