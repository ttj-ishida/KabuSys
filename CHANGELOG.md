# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全てのリリースは semver に従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回リリース。KabuSys の基盤機能を実装しました（環境設定、データ取得/保存、特徴量計算、ニュース収集、スキーマ定義など）。

### Added
- 基本パッケージ構成を追加
  - パッケージトップ: kabusys (バージョン 0.1.0)
  - 空のサブパッケージプレースホルダ: execution, strategy, monitoring

- 環境設定モジュール（kabusys.config）
  - .env ファイルと環境変数を読み込む自動ロード機能（プロジェクトルートの自動検出：.git / pyproject.toml を基準）
  - .env の行パーサ実装（export プレフィックス、クォート、インラインコメント対応）
  - .env/.env.local の読み込み順（OS 環境変数 > .env.local > .env）、既存値保護（protected）対応
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ
  - Settings クラスにより型付きプロパティで設定値を取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境判定、ログレベルバリデーション等）
  - KABUSYS_ENV / LOG_LEVEL の入力検証（有効値のチェック）

- データ API クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等）
  - レート制限制御（固定間隔スロットリングで 120 req/min を保証する RateLimiter）
  - 再試行ロジック（指数バックオフ、最大リトライ回数、429/408/5xx のリトライ処理、Retry-After ヘッダ優先）
  - 401 の場合はリフレッシュトークンで自動的に id_token を更新して再試行（無限再帰防止）
  - ページネーション対応の fetch_* 関数（pagination_key によるループ）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等保存を実現
  - データ変換ユーティリティ (_to_float, _to_int) を実装（安全な型変換と None ハンドリング）
  - fetched_at を UTC isoformat で記録（Look-ahead bias の追跡を容易に）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得・パース・DB 保存の総合実装
  - defusedxml を用いた安全な XML パース（XML Bomb 等の対策）
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES、10MB）および gzip 解凍時の追加検査（Gzip bomb 対策）
  - SSRF 対策：
    - URL スキーム検証（http/https のみ許可）
    - ホストがプライベート/ループバック等かを判定してブロック（DNS 解決し A/AAAA を検査）
    - リダイレクト時にもスキーム・ホスト検査を行うカスタム RedirectHandler を使用
  - トラッキングパラメータ除去・URL 正規化（utm_* 等を削除、クエリソート、フラグメント削除）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を採用して冪等性を保証
  - テキスト前処理（URL 除去・空白正規化）
  - DB 保存はチャンク化してトランザクション内で実行、INSERT ... RETURNING を用いて実際に挿入されたレコードID/件数を返す実装
  - 銘柄コード抽出（4桁数字パターン）と known_codes による絞り込み
  - run_news_collection により複数ソースをまとめて収集・保存し、銘柄紐付けを一括挿入

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema に基づく初期 DDL を追加（Raw/Processed/Feature/Execution 層の方針）
  - raw_prices, raw_financials, raw_news 等のテーブル定義（型制約・CHECK 制約・PRIMARY KEY を含む）
  - スキーマに対するログ出力を備える

- 研究用モジュール（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 将来リターンを DuckDB の prices_daily テーブルから一括取得（LEAD を使用）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（ランク付け関数 rank を内部実装）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median 計算（None/NaN を除外）
    - rank: 同順位は平均ランクを返す実装（round で ties の検出を安定化）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）の計算（ウィンドウ関数）
    - calc_volatility: 20日 ATR / 相対ATR / 20日平均売買代金 / 出来高比 の計算（true_range を正確に扱う）
    - calc_value: raw_financials の最新財務情報と prices_daily を結合して PER / ROE を計算
  - これらは外部ライブラリ（pandas 等）に依存せず標準ライブラリ＋DuckDB SQL で動作する設計

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサに defusedxml を採用し XML 攻撃に対処
- RSS フェッチ/リダイレクトで SSRF 防止のためスキーム/ホストチェックを実施
- API クライアントで 401 時のトークンリフレッシュ処理を導入し、再試行時の無限ループを回避
- .env 読み込みは OS 環境変数の保護（protected set）をサポート

### Notes / Known limitations
- strategy、execution、monitoring パッケージは現状プレースホルダ（実装なし）
- DuckDB スキーマに依存するため、利用前にスキーマ初期化が必要
- NewsCollector の既定 RSS ソースは最小構成（DEFAULT_RSS_SOURCES に Yahoo Finance のカテゴリ RSS を設定）
- jquants_client は内部で urllib を使用しているため、より高度な HTTP 機能（プロキシ認証・コネクションプール等）が必要な場合は将来的に HTTP クライアントの差し替えを検討
- calc_forward_returns / factor 計算は営業日数（連続レコード）を前提にしている点に注意

---

（この CHANGELOG はコードベースから推測して作成しています。実際のコミットログやリリース履歴がある場合はそちらに合わせて修正してください。）