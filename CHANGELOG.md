# CHANGELOG

すべての変更は Keep a Changelog の規約に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお本ファイルは、提供されたソースコードの内容から機能・設計・注意点を推測して作成した初期の変更履歴です。

## [Unreleased]

- なし

---

## [0.1.0] - 2026-03-18

初回リリース — KabuSys 基盤機能の実装（日本株自動売買／データプラットフォーム向けのコアライブラリ）。

### Added
- パッケージ基礎
  - パッケージメタ情報（kabusys.__init__）を追加。バージョンは 0.1.0。
  - サブパッケージの公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定管理
  - 環境変数 / .env ファイル読み込み用モジュール（kabusys.config）を追加。
    - .env と .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を実装（テスト時に有用）。
    - export KEY=val 形式やクォート付き値、インラインコメント処理に対応する堅牢な .env パーサを実装。
    - settings オブジェクトでアプリケーション設定を提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、実行環境、ログレベル など）。
    - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とヘルプメッセージ。

- データアクセス / ETL
  - DuckDB スキーマ定義モジュール（kabusys.data.schema）を追加。
    - Raw レイヤーのテーブル定義（raw_prices, raw_financials, raw_news, raw_executions 等）の DDL を定義。
    - （注）提供ソースの末尾で raw_executions の定義が途中で切れているため、実装途中の箇所が存在。

  - J-Quants API クライアント（kabusys.data.jquants_client）を追加。
    - 日足・財務・マーケットカレンダーの取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。ページネーション対応。
    - API レート制御（固定間隔スロットリング）を実装（デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）、429 に対しては Retry-After ヘッダ優先。
    - 401 受信時の自動トークンリフレッシュ（get_id_token を呼び出して 1 回だけリトライ）をサポート。モジュールレベルの ID トークンキャッシュでページネーション間のトークン共有を行う。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。取得時刻(fetched_at)を UTC で記録し、ON CONFLICT DO UPDATE による冪等保存を実現。
    - 型変換ユーティリティ（_to_float, _to_int）を提供し、入力の堅牢性を確保。

  - ニュース収集モジュール（kabusys.data.news_collector）を追加。
    - RSS フィードから記事を取得し raw_news に保存するワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - セキュリティ対策: defusedxml による XML パース、SSRF 対策（リダイレクト先の検査、プライベートIP/ホストの検出）、許可スキームの制限（http/https のみ）、受信サイズの上限設定（10MB）や Gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、パラメータソート）と記事 ID（SHA-256 の先頭 32 文字）による冪等性確保。
    - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、known_codes によるフィルタリング）。
    - DB 保存はチャンク化・トランザクションで実行し、INSERT ... RETURNING により実際に挿入された件数を正確に返す。

- 研究（Research）機能
  - ファクター計算モジュール（kabusys.research.factor_research）を実装。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）を DuckDB の prices_daily を参照して計算。
    - Volatility: 20 日 ATR（平均 true range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials と prices_daily を組み合わせて PER・ROE を計算（最新の報告日ベース）。
    - 計算は SQL（DuckDB）でウィンドウ関数を多用して実装。データ不足時は None を返す設計。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を実装。
    - 将来リターン計算（calc_forward_returns）：target_date の終値から各ホライズン（デフォルト 1,5,21 営業日）までのリターンを計算。単一クエリでリードを取得。
    - IC（Information Coefficient）計算（calc_ic）：ファクター値と将来リターンのスピアマンランク相関を計算。ランク関数（rank）において同順位は平均ランクで扱い、浮動小数点の ties を round(..., 12) で扱う。
    - factor_summary：指定カラムの count/mean/std/min/max/median を算出（None を除外）。
    - 研究用ユーティリティは標準ライブラリのみで記述（pandas など外部依存を最小化）。

- 公開モジュール
  - kabusys.research.__init__ で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize（外部に依存）など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集に関する複数のセキュリティ対策を実装:
  - defusedxml の利用による XML 攻撃防御。
  - SSRF 対策（リダイレクトハンドラでスキームとホスト/IP を検査、プライベートアドレスへの到達を拒否）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）や Gzip 解凍後のサイズチェックを導入し DoS を緩和。
  - URL スキーム検証により file:, javascript:, mailto: 等の不正スキームを排除。

### Notes / Usage
- 環境変数（必須）
  - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb
  - SQLite: data/monitoring.db
- 自動 .env ロード
  - プロジェクトルートの .env を自動で読み込み、.env.local による上書きをサポート（OS 環境変数は保護）。
- J-Quants API
  - レート上限 120 req/min を想定。RateLimiter により固定間隔でスロットリング。
  - 401 でのトークン自動リフレッシュ、リトライロジック（408/429/5xx）を実装。
  - DuckDB への保存は ON CONFLICT DO UPDATE を使い冪等性を確保。

### Known limitations / TODO
- schema.py の raw_executions の DDL がソース提供時に途中で切れている（未完了）。実運用前に Execution レイヤの DDL 完全化が必要。
- research モジュールは標準ライブラリ中心で実装しているため、高速データ処理や高度な統計機能（pandas, numpy 等）を用いた最適化は今後の拡張で検討。
- news_collector の HTTP クライアントは urllib を使用しているため、より豊富な機能（接続プール、タイムアウト制御、リトライ等）が必要なら requests / httpx などの導入を検討。
- Slack や kabu API を用いた実際の発注・監視ロジックは strategy / execution / monitoring パッケージで実装予定（現状はパッケージ構成のみ）。

---

発行者: KabuSys 開発チーム（コードベースの内容に基づく推測による CHANGELOG）