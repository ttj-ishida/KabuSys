Keep a Changelog に準拠した CHANGELOG.md（日本語）
※この変更履歴は同梱されたコードベースの内容から推測して作成しています。

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

---

# CHANGELOG

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
最初の公開リリース。本バージョンで導入された主要機能と実装上の注意点を列挙します。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - サブパッケージ候補として data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みするロジックを追加。
    - プロジェクトルートは __file__ から親ディレクトリを探索して .git または pyproject.toml を基準に特定。
    - 優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース実装（export プレフィックス、クォート／エスケープ、インラインコメント処理対応）。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境モード / ログレベル判定 等）。
    - 必須キー取得時は未設定で ValueError を送出する _require を実装。
    - env/log_level のバリデーション（許容値チェック）。

- データ取得 & 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライ戦略（最大 3 回、指数バックオフ、HTTP 408/429/5xx 対象）。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライする仕組み。
    - ID トークンのモジュールレベルキャッシュを導入（ページネーション間で共有）。
  - API 呼び出しユーティリティ _request と認証 get_id_token を提供。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
    - 取得時に fetched_at （UTC）を記録する設計思想を反映。
  - DuckDB への保存関数（冪等性を確保: ON CONFLICT DO UPDATE を使用）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - PK 欠損行のスキップとログ出力、保存件数の返却。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news に保存するモジュールを実装。
  - セキュリティ対策と堅牢性：
    - defusedxml を使用して XML Bomb 等に対応。
    - SSRF 対策: リダイレクト先のスキーム検証、プライベートIP/ループバック/リンクローカルの拒否（DNS 解決して A/AAAA を検査）。
    - URL スキーム検証（http/https のみ許可）、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を設置。
    - gzip 圧縮レスポンスの安全な解凍とサイズチェック（Gzip bomb 対策）。
  - RSS パースと前処理:
    - URL 正規化（トラッキングパラメータ除去、キーソート、フラグメント削除）。
    - 記事ID を正規化 URL から SHA-256 の先頭32文字で生成し冪等性を保証。
    - テキスト前処理（URL除去・空白正規化）。
    - RSS pubDate のパース（RFC 形式 → UTC naive datetime）とフォールバック。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのみを返す実装（チャンク化してトランザクションで実行）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で挿入（重複除去、トランザクション管理）。
  - 銘柄コード抽出: テキスト中の 4 桁数字を known_codes に照合して抽出するユーティリティ extract_stock_codes。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリ RSS を追加。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用のDDLを幅広く定義（Raw / Processed / Feature / Execution レイヤー）。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed テーブル。
    - features, ai_scores など Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution テーブル。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) を実装し、必要に応じて親ディレクトリ作成のうえ全DDLとインデックスを冪等的に適用して接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入（取得/保存件数、品質チェック結果、エラー集約などを格納）。
  - DB ヘルパー:
    - テーブル存在チェック、最大日付取得などのユーティリティを実装。
    - 市場カレンダーに基づく営業日調整ヘルパー _adjust_to_trading_day。
  - 差分更新ロジック（基本方針）と run_prices_etl の骨組みを実装:
    - 最終取得日から backfill_days 前を date_from として差分取得する方式（デフォルト backfill_days=3）。
    - jq.fetch_daily_quotes → jq.save_daily_quotes を呼ぶ処理フローを実装。

### Security
- RSS収集でのセキュリティ改善:
  - defusedxml を使用した XML パース（XML関連攻撃の緩和）。
  - SSRF 回避のための事前検証とリダイレクト検査。
  - 受信データサイズ上限と Gzip 解凍後のサイズ検査を実装。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を導入。

### Performance / Reliability
- API 呼び出しでのレートリミッタ実装により J-Quants のレート上限を順守。
- ID トークンのキャッシュでページネーション取得の効率化。
- API 呼び出しに対するリトライ（指数バックオフ、Retry-After 考慮）。
- DB 挿入はチャンク化・トランザクション化してオーバーヘッドを低減。
- INSERT ... RETURNING により実際に挿入された件数を正確に取得。

### Known issues / Notes
- run_prices_etl の戻り値に関する実装不整合:
  - run_prices_etl は (取得件数, 保存件数) を返す仕様になっているが、現行実装の最後の return 文は len(records), という形（片方のみの戻り値・末尾カンマ）になっており期待されるタプルを返していない可能性があります。テストや呼び出し側での取り扱いに注意が必要です（修正推奨）。
- strategy, execution, monitoring サブパッケージは現在 __init__ のみで、具体的実装は未提供。
- schema の制約やチェック（CHECK, FOREIGN KEY）が存在するため、保存前に型や NULL 制約を満たすデータ整形を行う必要あり。
- J-Quants API のレスポンススキーマ変化や未想定ケースに備えて追加の検証が必要になる場合があります。

### Removed
- なし

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

---

将来的なリリースでの改善提案（参考）
- run_prices_etl の戻り値修正と単体テスト追加。
- pipeline における quality モジュールの統合（欠損／スパイク検知の自動実行）。
- strategy / execution / monitoring の実装と E2E テスト。
- jquants_client の非同期版や接続プール化、並列取得時のレート制御強化。
- news_collector のソース設定管理（外部設定化）とフェイルオーバー戦略。

---
この CHANGELOG はコードベースの静的解析に基づく推定であり、実際のコミット履歴や意図と差異がある可能性があります。追加の変更履歴やリリース情報があれば更新してください。