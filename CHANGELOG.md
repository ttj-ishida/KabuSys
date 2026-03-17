# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
このファイルはリポジトリのコードベースから推測して作成した初期リリースの変更履歴です。

全体方針:
- SemVer を想定（パッケージ内 __version__ = "0.1.0" に準拠）
- 初回公開リリースとして 0.1.0 を登録

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を導入。

### Added
- パッケージ基盤
  - パッケージメタ情報（src/kabusys/__init__.py）。初期バージョン番号と公開モジュール一覧を定義。
  - 空のサブパッケージのプレースホルダ: strategy, execution, monitoring（将来の拡張用）。

- 設定管理
  - src/kabusys/config.py を追加。以下の機能を提供:
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の優先順位や既存 OS 環境変数保護の仕組みを実装。
    - .env の行パースの実装（コメント、export 形式、クォート/エスケープ、インラインコメント処理に対応）。
    - 自動ロードの無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - Settings クラスによるアクセス（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、実行環境・ログレベル判定など）。
    - 入力検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）とヘルパーメソッド（is_live/is_paper/is_dev）。

- データ取得クライアント（J-Quants）
  - src/kabusys/data/jquants_client.py を追加。主な特徴:
    - API 呼び出しのための汎用リクエスト関数（JSON デコードチェック、タイムアウト）。
    - レート制限（固定間隔スロットリング: 120 req/min を守る _RateLimiter）。
    - 冪等性を考慮したページネーション対応の取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）と 429 の Retry-After 対応。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して1回リトライする仕組み。
    - id_token のモジュールレベルキャッシュでページネーション間のトークン共有を実現。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）：
      - ON CONFLICT DO UPDATE による冪等保存
      - PK 欠損行のスキップとログ
      - fetched_at を UTC で記録（Look-ahead Bias 対策）
    - 型変換ユーティリティ (_to_float, _to_int) の堅牢な実装（空値、文字列数値、少数部の扱いなど）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を追加。主な特徴:
    - RSS フィードから記事を収集し raw_news テーブルへ保存するフローを実装。
    - セキュリティ／堅牢性:
      - defusedxml を使った XML パース（XML Bomb 対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカル判定、リダイレクト先検査を行うカスタム RedirectHandler。
      - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後検査。
      - 不正スキームや大きすぎるレスポンスの扱いで安全にスキップ。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES に基づく）。
    - 記事 ID を正規化 URL の SHA-256 先頭32文字で生成（冪等性確保）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出（4桁数字、既知銘柄セットでフィルタ、重複除去）。
    - DB 保存処理:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING WITH RETURNING、チャンク挿入、トランザクション管理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク・トランザクションで保存し、実際に挿入された件数を正確に返す。
    - 高レベルジョブ run_news_collection: 複数ソースの独立処理、新規挿入記事に対する銘柄紐付けの一括登録。

- スキーマ定義 / DB 初期化
  - src/kabusys/data/schema.py を追加。主な特徴:
    - Raw / Processed / Feature / Execution の各レイヤー向けテーブル DDL を定義。
    - 各テーブルの制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を明示。
    - インデックス定義（頻出アクセス向け）。
    - init_schema(db_path) によりディレクトリ作成、全テーブルとインデックスを冪等に作成して接続を返す。
    - get_connection(db_path) による既存 DB への接続。
    - データモデルは DataSchema.md 準拠（推測に基づく注記）。

- ETL パイプライン
  - src/kabusys/data/pipeline.py を追加。機能:
    - ETLResult dataclass による ETL 実行結果の集約（品質問題、エラー、取得/保存件数など）。
    - テーブル存在チェック、最大日付取得ユーティリティ。
    - 市場カレンダーに基づく取引日調整ヘルパー（_adjust_to_trading_day）。
    - 差分更新ロジックのためのヘルパー関数（get_last_price_date 等）。
    - run_prices_etl の差分ETL骨子（date_from の自動決定、backfill_days のサポート、最小取得開始日の設定、fetch + save の組合せ）。

### Security
- RSS フェッチ周りで SSRF 対策と外部からの悪意あるペイロード（XML Bomb、Gzip Bomb）対策を導入。
- .env 読み込みで OS 環境変数の上書きを制御する protected 機構を実装し、テストやCI環境での安全性を向上。

### Internal / Development
- 詳細な docstring と使用例・設計意図コメントを各モジュールに追加（テストや運用のための注記含む）。
- jquants_client のログ出力（info/warning/exception）を充実させて運用時のトラブルシュートを容易に。

### Breaking Changes
- 初回リリースのため該当なし。

---

補足:
- 上記 CHANGELOG はソースコードの内容と docstring から推測して作成しています。実際のリリースノートでは、コミット履歴や変更差分、貢献者情報、既知の制限事項を併せて記載することを推奨します。