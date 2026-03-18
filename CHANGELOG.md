# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般的な注意:
- 本リポジトリはバージョン 0.1.0 で初回公開されています。
- 多くの機能が DuckDB を前提に実装されており、prices_daily / raw_* テーブル等のスキーマが存在することが前提です。
- Strategy / Execution パッケージのエントリは用意されていますが、実装は本バージョンでは最小限または空の状態です。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ初期リリース: kabusys - 日本株自動売買システムの骨格を追加。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env のパース機能を実装（コメント、export プレフィックス、クォート文字列、インラインコメント処理などに対応）。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを実装し、J-Quants トークン、kabu API パスワード、Slack 設定、DB パスなど主要設定をプロパティとして提供。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。
  - 必須環境変数未設定時に ValueError を送出する _require() を実装。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限管理（固定間隔スロットリング、120 req/min を想定した RateLimiter）。
  - HTTP リクエストラッパーにリトライ（指数バックオフ）、429/408/5xx の再試行ロジックを実装。
  - 401 Unauthorized 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組みを実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 実装。
  - DuckDB への冪等的保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT を使って既存レコードを更新。
  - 文字列→数値の変換ユーティリティ (_to_float / _to_int) を実装し、不正値や空値に対する寛容性を確保。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias の追跡に配慮。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集して raw_news, news_symbols へ保存するフローを実装。
  - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）と記事 ID 生成（SHA-256 の先頭32文字）。
  - SSRF 対策:
    - fetch 前にホストのプライベートアドレスチェックを実施。
    - リダイレクト時にスキーム／ホストの検査を行うカスタム RedirectHandler を導入。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Gzip 圧縮の解凍後も再チェック。
  - コンテンツ前処理関数（URL 除去、空白正規化）。
  - DB への保存はチャンク化してトランザクション内で実行し、INSERT ... RETURNING により実際に挿入された記事ID / 件数を正しく返す実装。
  - テキストから銘柄コード抽出（4桁数字）および既知銘柄セットによるフィルタリング機能を実装。
  - 全ソースを巡回して収集する run_news_collection を実装（各ソースは個別にエラーハンドリングし、1ソース失敗でも継続）。

- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを DuckDB の prices_daily を参照して計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算する実装（ties の平均ランク処理を含む）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティ。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（浮動小数点誤差対策の丸めを含む）。
    - 設計方針として外部ライブラリ（pandas 等）に依存しない純標準ライブラリ実装を採用。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を prices_daily から計算。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。true_range の NULL 伝播を正確に制御。
    - calc_value: raw_financials から最新の財務データを取得し、PER / ROE を計算（EPS が 0 または NULL の場合は PER を None にする）。
    - 各関数は データ不足時に None を返す設計（ウィンドウ未満等）。
    - DuckDB に対する SQL + ウィンドウ関数を多用した実装でパフォーマンスを意識。

- スキーマ (kabusys.data.schema)
  - DuckDB 用の DDL 定義を追加（raw_prices / raw_financials / raw_news / raw_executions 等のテーブル定義の雛形）。
  - DataLayer の三層（Raw / Processed / Feature / Execution）のコンセプトに沿ったスキーマ設計開始。

- パッケージエクスポート
  - kabusys.research.__init__ に主要関数を公開する __all__ を設定（calc_momentum 等）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector において SSRF / XML Bomb / 大容量レスポンス対策を実装。
- J-Quants クライアントにおいてトークンの安全なリフレッシュと再試行制御を実装。

### 注記 / 既知の制約 (Notes / Known issues)
- Strategy / Execution パッケージは API のエントリを用意しているものの、発注ロジックや実口座との接続は本バージョンで含まれていません（空の __init__）。運用には追加実装が必要です。
- research モジュールは DuckDB の特定テーブル構造（prices_daily, raw_financials 等）を前提に動作します。データ整備後に正しく動作します。
- jquants_client のレート制限は固定間隔スロットリングで実装しており、複数プロセス／複数ホストで同一 API キーを共有するケースでは別途対策（分散レートリミッタ等）が必要です。
- news_collector は defusedxml を使用しているため、ランタイム環境に該当パッケージが必要です（依存関係の管理に注意）。

---

今後の予定（例）
- Strategy / Execution の具体的な発注・ポジション管理ロジックの追加。
- モニタリング・アラート（Slack 連携含む）の実装充実。
- テストカバレッジの拡充、CI / CD パイプラインの整備。

（以上）