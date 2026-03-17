# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
安定版リリースはセマンティックバージョニングに従います。

## [Unreleased]

### Added
- ドキュメント・メタ情報の追記/整理（パッケージ初期化情報など）

### Changed
- なし

### Fixed
- なし

### Security
- なし

---

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。以下はコードベースから推測される主要な機能追加と設計上のポイントです。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - public API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定モジュール (`kabusys.config`)
  - .env ファイルおよび環境変数から設定をロードする自動ローダーを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装し、CWD に依存しない読み込みを実現。
  - .env, .env.local の優先順位と上書きルール（OS 環境変数の保護）をサポート。
  - 行パーサーは export 形式・コメント・クォート・エスケープに対応。
  - 必須設定取得用の `_require()` と `Settings` クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境・ログレベル検証など）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を実装（テスト向け）。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する機能を実装。
  - レートリミッタ（固定間隔スロットリング）により API レート制限（120 req/min）を順守。
  - 再試行（指数バックオフ）ロジックを実装（最大 3 回、408/429/5xx を対象）。429 時は Retry-After を優先。
  - 401 受信時の自動トークンリフレッシュ（1 回まで）を実装。ページネーション間で ID トークンをモジュールキャッシュで共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB へ冪等的に保存する save_* 関数を実装（ON CONFLICT DO UPDATE）。
  - 取得時刻（fetched_at）を UTC ISO フォーマットで記録し、Look-ahead bias 防止を考慮。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集して raw_news に保存する一連の機能を実装。
  - トラッキングパラメータ除去・URL 正規化（小文字化・クエリソート・フラグメント削除）と SHA-256 ベースの記事ID生成（先頭32文字）による冪等性確保。
  - defusedxml を利用した XML パースで XML Bomb 等の攻撃を軽減。
  - SSRF 対策：URL スキーム制限（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト先の検査を実装。
  - レスポンス受信バイト数上限（10 MB）と gzip 解凍後サイズ検査を導入（Gzip bomb 対策）。
  - content:encoded を優先するパーシング、多様なフィードレイアウトへのフォールバックを実装。
  - DuckDB へチャンク単位での一括挿入（INSERT ... RETURNING）を行い、実際に挿入された記事IDのリストを返す。
  - 銘柄抽出機能（4桁の数字パターン）と news_symbols への紐付け処理を実装。既知銘柄セットによるフィルタリングと重複排除。

- スキーマ管理モジュール (`kabusys.data.schema`)
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution の 3 層構造）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル、processed/feature/execution 各層のテーブルを作成する DDL を提供。
  - インデックス定義と外部キー依存順を考慮したテーブル作成順を実装。
  - `init_schema(db_path)` で親ディレクトリ自動作成・テーブル初期化を行い、接続を返す。`:memory:` 対応あり。
  - `get_connection(db_path)` で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプラインモジュール (`kabusys.data.pipeline`)
  - 差分更新（最終取得日を元に未取得分のみ取得）と backfill（デフォルト 3 日）による後出し修正吸収機能を実装。
  - 市場カレンダーの先読み（デフォルト 90 日）などの運用ヘルパーを定義。
  - ETL 実行結果を表す `ETLResult` データクラス（品質問題・エラー集約・シリアライズ機能付き）を提供。
  - テーブル存在チェック、最大日付取得ヘルパー、営業日調整ロジックを実装。
  - run_prices_etl 等の個別 ETL ジョブを実装（差分取得・保存・ログ出力）。

### Fixed / Behavior
- .env 解析の堅牢化
  - export prefix に対応、クォートされた値でのバックスラッシュエスケープ処理、インラインコメントの扱いを改善。
  - コメントの認識ルール（クォートなしの '#' は直前が空白/タブの場合にコメントとみなす）を明確化。

- 数値変換の厳密化（jquants_client）
  - _to_float/_to_int の実装により空値・不正値は None を返す仕様に統一。
  - float 文字列を int に変換する際、1.0 のように小数部がゼロのもののみ変換し、切り捨てを防止。

- NewsCollector の堅牢化
  - 非URL GUID、mailto/file スキームのリンク等をスキップすることで不正データを排除。
  - XML パース失敗や大きすぎるレスポンスは安全にスキップして運用継続可能に。

### Security
- SSRF 対策強化（news_collector）
  - リクエスト前のホストチェック、リダイレクト先のスキーム/ホスト検査を実装。
  - 許可スキームは http / https のみ。
  - プライベート/ループバック/リンクローカル/マルチキャストアドレスへの到達を防止。
- XML パースの安全化
  - defusedxml を用いて XML ベースの攻撃耐性を向上。
- 環境変数保護
  - .env ファイル読み込み時に既存 OS 環境変数を保護する仕組みを導入（.env.local の override 動作は制御）。

### Notes / Limitations
- 現時点でのエラーハンドリングはログ出力と部分継続を前提にしており、呼び出し元での再試行戦略や通知（例: Slack 送信）は別モジュール/運用で実装する想定です。
- DuckDB の INSERT 文はプレースホルダを直接埋める実装があるため、埋め込み SQL の取り扱いに注意が必要（現状はパラメータ化して実行）。
- get_id_token の POST 呼び出しは _request 経由で行われ、allow_refresh=False によって無限再帰を回避していますが、外部トークン関係の障害シナリオの追加テストを推奨します。
- news_collector の既知銘柄セット（known_codes）は外部で用意する必要があり、カバレッジはそのセットに依存します。

### Deprecated
- なし

### Removed
- なし

---

貢献・報告
- バグや改善提案があれば Issue を立ててください。必要に応じて CHANGELOG を更新します。