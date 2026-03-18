# Changelog

すべての重要な変更点を記録します。  
このプロジェクトは Keep a Changelog の慣習に従っており、セマンティックバージョニングを採用しています。

- リリースノートに記載されていない内部実装の改善やリファクタリングも行われる場合があります。
- 日付はリリース日です。

## [Unreleased]

## [0.1.0] - 2026-03-18

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - パッケージ公開時に利用する __all__ を定義（data, strategy, execution, monitoring）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
  - .env の詳細なパースロジック（export 形式、クォート/エスケープ、インラインコメント扱いなど）を実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得時のバリデーション (_require) と enum 検査（KABUSYS_ENV, LOG_LEVEL）。
  - 主要設定プロパティを用意（J-Quants トークン、kabu API、Slack、DuckDB/SQLite パス等）。
- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）を行うクライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 等）と 429 の Retry-After 優先対応。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応（pagination_key の処理）。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を提供（raw_prices, raw_financials, market_calendar）。
  - 取得時刻（fetched_at）を UTC ISO 8601 形式で記録し、Look-ahead バイアス対策を考慮。
  - 型変換ユーティリティ（_to_float, _to_int）を提供（安全な変換と None の扱い）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して DuckDB に保存する機能を実装（raw_news / news_symbols）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム制限 (http/https のみ)、ホストのプライベートアドレス判定、リダイレクト先検査用カスタムハンドラ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査。
    - 不正なスキームや過大レスポンスはスキップして安全に処理。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事ID生成（normalized URL の SHA-256 先頭32文字）で冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）。
  - 大量挿入時のチャンク化とトランザクション管理（INSERT ... RETURNING を利用し実際に挿入されたIDを返す）。
  - 銘柄コード抽出ユーティリティ（4桁の数値パターン）と記事-銘柄紐付けの一括保存機能。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。
- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層を含む完全な DuckDB スキーマ定義を追加。
  - 各種テーブル（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）と制約・チェック・外部キー・インデックスを用意。
  - init_schema(db_path) によりディレクトリ作成、DDL 実行、インデックス作成を行い接続を返す。get_connection() で既存 DB へ接続可能。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL パイプラインの基礎を実装（差分取得、保存、品質チェックフックに対応）。
  - ETLResult dataclass により ETL 結果、品質問題、エラーを集約して返却可能。
  - データ最古日やカレンダーの先読み日数定数、バックフィル挙動のデフォルト（3日）などを設定。
  - テーブル存在チェック、最大日付取得ヘルパー、営業日調整ロジックを実装。
  - run_prices_etl の骨組み（差分計算、fetch -> save 流れ）を実装（取得範囲の自動決定、backfill 対応）。
- その他
  - 各モジュールに詳細な設計方針・セキュリティ考慮点をコメントで明記。
  - テストフレンドリーな設計（_urlopen の差し替え、id_token 注入等）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- XML 外部実行攻撃や XML Bomb に備え defusedxml を使用。
- RSS フィード取得で SSRF 対策（スキーム制限、プライベートIP検出、リダイレクト時検査）。
- レスポンスサイズ制限や gzip 解凍後のサイズチェックでメモリ DoS を軽減。
- .env パーサは意図しない展開やコメント解釈の攻撃を考慮した実装。

### 既知の制約・未実装（注意事項）
- strategy/, execution/, monitoring/ パッケージは初期のプレースホルダ（__init__.py が空）として用意されています。各サブモジュールの具体的な戦略・発注ロジックは今後追加予定です。
- run_prices_etl 等の ETL ジョブは骨格が実装されていますが、完全な品質チェックフロー（quality モジュールの導入・検査処理の詳細）は別途実装が必要です。
- SQLite/DuckDB の接続設定は defaults を提供していますが、本番環境では環境変数でパス・資格情報を適切に設定してください。

---

今後のリリースでは、戦略実装、発注実行モジュール、監視・アラート連携（Slack 通知等）の追加、品質チェックルールの拡充を予定しています。