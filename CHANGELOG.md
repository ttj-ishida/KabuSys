CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

初回リリース。日本株の自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。主な追加点は以下のとおりです。

Added
- パッケージ骨組み
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン定義 (0.1.0) を追加。
  - strategy/、execution/、monitoring/ のモジュールプレースホルダを追加。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を追加。自動ロード順序は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
  - .git または pyproject.toml を基準にプロジェクトルートを探索する実装（CWD に依存しない）。
  - export KEY=val 形式、クォートやインラインコメントを考慮した .env 行パーサを実装。
  - 必須環境変数取得ヘルパ（_require）と Settings クラスを追加。J-Quants / kabu / Slack / DB パスや環境（development/paper_trading/live）やログレベルの検証を含む。

- J-Quants データクライアント（src/kabusys/data/jquants_client.py）
  - 株価日足、財務データ、マーケットカレンダー取得用の API クライアントを実装。
  - API レート制御（_RateLimiter）: 120 req/min を固定間隔スロットリングで厳守。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。対象は 408/429/5xx 等のネットワーク／サーバエラー。
  - 401 Unauthorized 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ（無限再帰防止）。
  - ページネーション対応（pagination_key による継続取得）。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装。fetched_at に UTC 時刻を記録して Look-ahead バイアスを排除。
  - 数値変換ユーティリティ（_to_float、_to_int）を実装し不正値に対処。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パースで XML-Bomb 等を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検査、リダイレクトハンドラでリダイレクト先も検証。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査でメモリ DoS を緩和。
    - トラッキングパラメータ（utm_* 等）の除去と URL 正規化。
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - raw_news へのバルク挿入はチャンク化およびトランザクションで行い、INSERT ... ON CONFLICT DO NOTHING RETURNING を使って実際に挿入された ID を取得。
  - 銘柄コード抽出 (extract_stock_codes): 4桁数字を候補として known_codes に基づき抽出。
  - run_news_collection により複数ソースを順次処理し、各ソースは独立してエラーハンドリング。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 3 層（+Execution 層）にまたがるテーブル定義を追加。
  - テーブル定義は冪等（CREATE TABLE IF NOT EXISTS）で記述。外部キー依存を考慮した作成順序を定義。
  - 頻出クエリに備えたインデックスを追加。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成を行い、全テーブルとインデックスを作成して接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない旨を明示）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL ジョブの基盤を追加。
  - 差分更新ロジック: DB の最終取得日から backfill_days を遡って再取得する（デフォルト backfill_days=3）。
  - 市場カレンダーは先読み（lookahead）を行う定数を導入。
  - ETLResult データクラスを追加し、フェッチ数・保存数・品質問題・エラーを集約して返せるようにした。
  - テーブル存在確認・最大日付取得等のユーティリティ関数を実装。
  - run_prices_etl の骨組みを実装（fetch -> save のフロー、取得範囲算出など）。

Changed
- （初回リリースのため過去リリースからの変更はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- RSS パーサに対する defusedxml の使用、SSRF 対策（スキーム/ホスト検証、リダイレクト検査）、レスポンスサイズ制限、gzip 解凍サイズ検査など複数の安全対策を導入。
- .env 読み込み時の既存 OS 環境変数保護（protected set）によりテストや CI の環境変数上書きを制御。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 環境種別は KABUSYS_ENV にて development / paper_trading / live のいずれかを指定。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効。
- DuckDB スキーマ作成は init_schema() を使用してください。既存 DB に接続する場合は get_connection() を利用し、初回は init_schema() を実行してください。
- ニュース収集時に銘柄抽出を有効にするには known_codes セットを渡してください（extract_stock_codes は 4 桁数字の銘柄コードを元にフィルタリングします）。

Known issues / TODO
- strategy/、execution/、monitoring モジュールは現状プレースホルダのため、実際の戦略実装・発注連携・監視機能は今後追加予定。
- pipeline.run_prices_etl の最後の戻り値タプルが未完（ソースから切り出された状態）になっている箇所があるため、ETL 完結処理と品質チェック統合は今後の対応対象。
- 一部の SQL は文字列結合で構築されている箇所があり（プレースホルダは使用しているがクエリ自体は f-string で組立て）、大きな入力に対する安全性や SQL 長の制限を注意する必要あり（現在はチャンク分割で対策済み）。

---

このリリースは基盤機能を整備することに注力しており、今後は戦略実装、発注実行の接続、監視・アラート機能、品質検査の強化などを順次追加予定です。