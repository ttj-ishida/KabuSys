# CHANGELOG

すべての重要な変更点は Keep a Changelog の規約に準拠して記載します。  
このファイルは、現行コードベースの内容から推測して作成した初期リリースの変更履歴です。

- フォーマット: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)
- バージョン: 0.1.0
- 日付: 2026-03-17

---

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システムの基盤となる以下の主要コンポーネントを実装。

### 追加 (Added)
- パッケージ基本設定
  - kabusys パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン情報 __version__ = "0.1.0" を設定。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルートの検出は __file__ を基準に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env の行パーサーを実装: export プレフィックス、クォート、エスケープ、インラインコメントの扱いに対応。
  - Settings クラスを実装し、アプリケーション設定（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル等）をプロパティ経由で安全に取得。
  - 環境変数の必須チェックおよび値検証（KABUSYS_ENV, LOG_LEVEL の妥当性検査）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベースの通信ユーティリティを実装（_request）。
    - レート制限 (120 req/min) を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 を検知した場合の自動トークンリフレッシュ（1回のみ）を実装。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
    - JSON デコードエラーやネットワーク例外のハンドリング。
  - 認証ヘルパー get_id_token(refresh_token: Optional[str]) を実装。
  - データ取得関数（ページネーション対応）を実装:
    - fetch_daily_quotes: 株価日足（OHLCV）。
    - fetch_financial_statements: 財務（四半期 BS/PL）。
    - fetch_market_calendar: JPX のマーケットカレンダー。
  - DuckDB への保存関数（冪等性を考慮）を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE により重複を排除／更新。
    - fetched_at（UTC）を記録し、Look-ahead bias のトレースを容易に。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集を実装。
    - defusedxml を利用して XML Bomb 等を防止。
    - SSRF 対策: URL スキーム検証（http/https 限定）、ホストがプライベート/ループバック/リンクローカルかの検査（DNS 解決を含む）、リダイレクト時の検査（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）および Gzip 解凍後の検査（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去（utm_ 等）。正規化した URL の SHA-256 先頭32文字を記事IDとして利用し冪等性を担保。
    - テキスト前処理（URL除去・空白正規化）。
    - fetch_rss: RSS 取得 -> XML パース -> 記事抽出（content:encoded 優先） -> NewsArticle 型で返却。
  - DuckDB への保存関数:
    - save_raw_news: INSERT ... RETURNING を使い新規挿入された記事IDのみを返す。チャンク挿入と単一トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括登録（ON CONFLICT DO NOTHING、INSERT RETURNING で実際の挿入数を返す）。
  - 銘柄コード抽出: テキストから4桁の候補を抽出し、known_codes セットでフィルタ（重複除去）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく3層（Raw / Processed / Feature / Execution）を意識したテーブル群を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）や適切なデータ型を定義。
  - 頻出クエリ向けのインデックスを複数定義。
  - init_schema(db_path) によりディレクトリ作成、テーブル・インデックス作成を行う初期化関数を提供（冪等）。
  - get_connection(db_path) による接続取得ユーティリティを提供（スキーマ初期化は行わない点に注意）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL の設計に基づくパイプライン基盤を実装:
    - 差分更新（最終取得日を確認し未取得分のみを取得）・バックフィルの概念（デフォルト backfill_days=3）。
    - ETLResult dataclass を定義し、取得／保存件数、品質問題、エラーを集約して返却。has_errors / has_quality_errors プロパティを提供。
    - テーブル存在チェック、最大日付取得などのヘルパー関数を実装。
    - 市場カレンダーを考慮した営業日調整ヘルパー _adjust_to_trading_day を実装。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
    - run_prices_etl を実装（差分取得→jq.fetch_daily_quotes→jq.save_daily_quotes、ログ出力）。（ETL ワークフローの一部を提供）

### セキュリティ (Security)
- ニュース収集周りのセキュリティ対策を多数実装:
  - defusedxml による XML パース（XML バグ・攻撃対策）。
  - SSRF 防止: スキーム検査、ホストがプライベートアドレスかの判定、リダイレクト先検査。
  - 応答サイズと解凍後サイズの上限チェックでメモリ DoS / Gzip bomb を防止。
- API クライアント側ではトークン管理と再試行、レート制限により外部 API 利用時の堅牢化。

### 変更 (Changed)
- 初回リリースのため変更点はなし（初実装）。

### 修正 (Fixed)
- 初回リリースのため修正履歴はなし。

### 既知の注意点 / 今後の改善提案
- run_prices_etl の実装は差分取得のロジックを備えていますが、現行ソースの末尾での戻り値処理が未完に見える（コードの取得状況により saved 値が返却されない可能性がある）。実運用前に戻り値の整合性（(fetched, saved) のタプルを常に返す）を確認・修正してください。
- strategy/execution/monitoring パッケージはエントリが存在するものの具体的な実装は含まれていない（インターフェース／骨組みを想定）。自動売買ロジック、発注処理、監視機能は別途実装が必要。
- テスト: ネットワーク依存の部分（J-Quants / RSS）についてはモック可能なフックを用意している（例: _urlopen の差し替え）が、ユニットテストの整備を推奨。
- DB の移行・スキーマ変更戦略（マイグレーション）については現状の init_schema は既存テーブルを保持するが、将来的なスキーマ変更時のマイグレーション機構が必要。

---

参照:
- パッケージ内のドキュメント文字列およびコードコメントに基づき作成。README や DataPlatform.md / DataSchema.md 等の設計資料が存在する想定。