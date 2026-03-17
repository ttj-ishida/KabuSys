# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」標準に準拠しています。

フォーマット:
- すべてのバージョンはリリース日付きで記載します。
- 変更はカテゴリ（Added、Changed、Fixed、Security、等）に分類します。

## [0.1.0] - 2026-03-17
初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な機能と設計上のポイントは以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ を "0.1.0" に設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

- 設定管理
  - 環境変数/設定管理モジュール（kabusys.config）を追加。
  - .env / .env.local の自動ロード機能（プロジェクトルートの自動検出: .git または pyproject.toml を基準）を実装。
  - .env 行パーサ（export 形式、クォートやインラインコメントへの対応）を実装。
  - 自動ロード無効化のための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスに J-Quants、kabu API、Slack、DB パス、実行環境（development/paper_trading/live）やログレベル判定などのプロパティを提供。
  - 必須環境変数未設定時に明示的なエラーを投げる _require 関数。

- データ取得クライアント
  - J-Quants API クライアント（kabusys.data.jquants_client）を追加。
  - API レート制限（120 req/min）に対応する固定間隔レートリミッタを実装。
  - リトライ戦略（指数バックオフ、最大 3 回）。HTTP 408/429/5xx を再試行対象に設定。
  - 401 (Unauthorized) 受信時はリフレッシュトークンから id_token を自動更新して 1 回再試行するロジックを実装（無限再帰防止）。
  - ページネーション対応で日足（OHLCV）、財務データ、マーケットカレンダーを取得する fetch_* 関数を実装。
  - 取得データを DuckDB に保存する save_* 関数を実装。ON CONFLICT DO UPDATE による冪等保存（fetched_at を UTC で記録）。
  - 型ヒント、ログ出力を充実化。

- ニュース収集
  - RSS ベースのニュース収集モジュール（kabusys.data.news_collector）を追加。
  - デフォルト RSS ソース（例: Yahoo Finance）を定義。
  - defusedxml を用いた安全な XML パース実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）、正規化 URL の SHA-256 先頭 32 文字を記事IDとして採用し冪等性を担保。
  - SSRF 対策:
    - リダイレクトを検査するカスタム HTTPRedirectHandler を実装（スキーム検証、プライベートアドレスへの到達拒否）。
    - フェッチ前のホスト事前検証、最終 URL の再検証、非 http/https スキーム拒否。
    - ホスト名の DNS 解決結果を検査し、プライベート/ループバック/リンクローカル/マルチキャスト IP をブロック。
  - レスポンスサイズの上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み込み時・gzip 解凍後の検査でメモリ DoS を軽減。
  - text 前処理（URL 除去・空白正規化）、記事保存時のトランザクション化とチャンク化（INSERT ... RETURNING を使用）による効率的なバルク保存。
  - 銘柄コード抽出（4桁数字パターン）と news_symbols への紐付けを行うユーティリティを追加。

- スキーマ管理 / DuckDB
  - DuckDB 用のスキーマ定義モジュール（kabusys.data.schema）を追加。
  - Raw / Processed / Feature / Execution 層を想定した多数のテーブル定義を実装（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, 等）。
  - インデックス定義（頻出クエリ向け）、外部キー制約、CHECK 制約を含む DDL を提供。
  - init_schema(db_path) による初期化、get_connection() による接続取得を提供。ファイルパス親ディレクトリの自動作成対応。
  - テーブル作成は冪等（IF NOT EXISTS）で実行。

- ETL パイプライン
  - ETL 用モジュール（kabusys.data.pipeline）を追加。
  - ETLResult データクラス（取得数・保存数・品質問題リスト・エラーリストなど）を実装。
  - DB 上の最終取得日を取得するユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 取引日調整ロジック（_adjust_to_trading_day）と差分更新ロジックの骨組みを実装。
  - run_prices_etl: 差分更新（最終取得日に基づく date_from の算出、バックフィル日数の指定）、fetch + save の流れを実装（ETL の一連の設計方針に沿った実装）。品質チェックは別モジュール（kabusys.data.quality）を利用する想定。

### Security
- ニュース収集に関して複数のセキュリティ対策を導入:
  - defusedxml による XML パース（XML Bomb 等対策）。
  - SSRF 対策（スキーム検証、プライベート IP チェック、リダイレクト検査）。
  - レスポンスサイズ制限と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - URL スキームの許可は http/https のみ。

### Performance / Reliability
- J-Quants API クライアントでレートリミッタを実装し API レート制限を遵守。
- リトライと指数バックオフ、429 の Retry-After ヘッダ優先処理により外部 API 呼び出しの堅牢性を向上。
- News 保存処理でチャンク化 & トランザクションを使用し DB への負荷を抑制。
- DuckDB DDL にインデックスを追加し、銘柄×日付などの頻出クエリを想定した最適化を実施。

### Other
- 型ヒント・logging を各モジュールに適用し可読性・保守性を向上。
- 各所に明確なエラーハンドリングと警告ログ出力を追加。

### Known issues / Notes
- pipeline.run_prices_etl の実装は差分更新の流れを提供していますが、品質チェック（quality モジュール）やその他 ETL ジョブ（財務・カレンダーのまとめ実行等）の統合は引き続き拡張を想定。
- strategy/execution/monitoring パッケージはパッケージ構造として定義されていますが、個別機能の本実装は今後のリリースで追加予定。

---

今後の予定（例）
- strategy モジュールに特徴量利用の戦略実装、execution モジュールに発注連携の実装、監視・アラート機能の強化。
- quality モジュールの実装拡充と ETL への自動対応ルール（自動ロールバックやアラート）追加。
- 単体テスト・統合テストの整備と CI/CD パイプラインの導入。

もし CHANGELOG に追記したい重点（例: もっと詳しい DB スキーマ変更履歴、デバッグ用ログ追加の履歴など）があれば教えてください。コードの差分や今後のリリース計画に合わせて更新案を作成します。