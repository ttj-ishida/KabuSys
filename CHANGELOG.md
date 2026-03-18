# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-18

### Added
- 初回リリース。パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として公開。
- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定は .git または pyproject.toml を起点に行い、CWD に依存しない設計。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 環境変数保護（既存 OS 環境変数を protected として上書きを制御）をサポート。
  - Settings クラスを公開し、J-Quants / kabu ステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの検証付きプロパティを提供。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - API 呼び出しユーティリティにレートリミッタ（120 req/min 固定間隔スロットリング）を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を導入。
  - 401 レスポンス時はリフレッシュトークンから id_token を自動更新して 1 回再試行する仕組みを実装。
  - id_token のモジュールレベルキャッシュを提供し、ページネーション間で共有。
  - 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）の取得を実装（ページネーション対応）。
  - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を考慮し DuckDB の ON CONFLICT DO UPDATE を使用して保存。
  - データ取得時に fetched_at を UTC ISO フォーマットで記録することで look-ahead bias を軽減。
  - 型変換ユーティリティ（_to_float, _to_int）に安全で明示的な変換ルールを実装（空値・不正値は None、"1.0" 等の文字列→ int 変換の注意点等）。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードから記事を取得して raw_news テーブルへ保存する一連の機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への防御）。
    - SSRF 対策としてリダイレクト前後でスキーム/ホスト検証とプライベートアドレス判定を実施（カスタム RedirectHandler, _is_private_host）。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査を実装（Gzip bomb 対策）。
  - URL 正規化機能を実装（追跡パラメータの削除、スキーム/ホストの小文字化、フラグメント削除、クエリソート）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理（URL削除、空白正規化）や pubDate の RFC 2822 パース（UTC 基準のフォールバック）を提供。
  - DuckDB への保存はトランザクション内でチャンク INSERT を行い、INSERT ... RETURNING を用いて実際に挿入された記事IDを返す（save_raw_news）。
  - 記事と銘柄コードの紐付けを行う save_news_symbols / _save_news_symbols_bulk を実装（ON CONFLICT DO NOTHING を利用し正確な挿入数を返す）。
  - 銘柄コード抽出ロジック（4桁数字パターン + known_codes フィルタ）を提供。
  - run_news_collection により複数ソースの収集を一括実行、ソース毎に独立してエラーハンドリング。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - DataPlatform 設計に基づいた 3 層（Raw / Processed / Feature）＋Execution 層のテーブル群を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを含む。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを含む。
  - features, ai_scores 等の Feature テーブル、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを含む。
  - 適切なチェック制約（CHECK）、PRIMARY KEY、外部キー、インデックスを定義。
  - init_schema(db_path) によりファイル/インメモリ DB を作成して全テーブル・インデックスを冪等的に初期化する API を提供。get_connection() も提供。

- ETL パイプラインの一部を実装（src/kabusys/data/pipeline.py）。
  - ETLResult Dataclass を導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー一覧など）を構造化して返却・監査可能に。
  - テーブル存在チェック、最大日付取得ユーティリティを実装。
  - market_calendar に基づく営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - 差分更新ロジックのヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を提供。
  - run_prices_etl を実装（差分取得、バックフィル対応、_MIN_DATA_DATE=2017-01-01、デフォルト backfill_days=3）。J-Quants クライアント経由で fetch -> save を実行。

- パッケージのサブパッケージ初期化ファイルを追加（src/kabusys/data/__init__.py、src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py）。将来の拡張に備えたプレースホルダ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサ・HTTP クライアント周りに SSRF、XML Bomb、Gzip Bomb、過大レスポンス対策を組み込み。DB 保存はトランザクションと ON CONFLICT により安全性・整合性を向上。

### Notes / Design decisions
- 冪等性重視: API から取得した生データは DuckDB へ ON CONFLICT を用いた上書き/無視で保存する方針を採用。
- ロギングと可視化: 各処理は logger を用いて情報・警告・例外を出力する設計（監査ログに利用可能な to_dict 等の補助あり）。
- ETL は Fail-Fast とせず、品質チェックの問題があっても収集は継続する設計（呼び出し元での対応判断を想定）。

---
今後のリリースでは、strategy / execution の具体的な戦略実装や発注連携（kabuステーション API 経由）、品質チェックモジュール (kabusys.data.quality) の具体実装、監視/通知機能（Slack 連携）などの追加を予定しています。