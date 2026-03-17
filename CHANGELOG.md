# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリのコードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

> なし

## [0.1.0] - 2026-03-17

最初の公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点・設計方針は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージメタ情報を `src/kabusys/__init__.py` に実装（version = 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring を公開。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出: `.git` または `pyproject.toml` を起点に探索して .env を読み込む。
  - `.env` の行パースに対応:
    - `export KEY=val` 形式のサポート、
    - クォートの取り扱い（バックスラッシュエスケープ含む）、
    - インラインコメント処理（クォート外での `#` を条件付きでコメント扱い）、
    - 無効行のスキップ。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを抑制可能（テスト用途）。
  - 環境値取得ユーティリティ `Settings` クラスを提供（J-Quants トークン、kabu API、Slack、DBパス、ログレベル、環境種別など）。
  - 環境変数の妥当性チェック:
    - KABUSYS_ENV: `development`, `paper_trading`, `live` のいずれかで検証。
    - LOG_LEVEL: 標準ログレベルで検証。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本機能:
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する関数を実装（ページネーション対応）。
  - レート制御:
    - 固定間隔スロットリングに基づく RateLimiter を実装（デフォルト 120 req/min）。
  - リトライ/エラーハンドリング:
    - 指数バックオフによるリトライ（最大3回、408/429/5xxを対象）。
    - 429 の場合は `Retry-After` ヘッダ優先。
  - 認証トークン管理:
    - refresh token から id_token を取得する `get_id_token` 実装。
    - 401 受信時は自動で id_token を1回リフレッシュしてリトライする仕組みを導入（無限再帰防止のため allow_refresh フラグを管理）。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有。
  - 取得データの保存:
    - DuckDB への保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を実装。
    - 冪等性を担保するため INSERT ... ON CONFLICT DO UPDATE を使用（PK重複時は更新）。
    - 取得時刻（fetched_at）を UTC ISO8601（Z）で記録し、Look-ahead bias を回避可能に。
  - データ変換ユーティリティ:
    - 安全な数値変換関数 `_to_float`, `_to_int` を実装（空値／不正値は None）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからの記事収集と DuckDB への保存処理を実装（設計書に沿った実装想定）。
  - セキュアな XML パースに defusedxml を使用して XML Bomb 等の攻撃を防御。
  - SSRF 対策:
    - リダイレクト検査用のカスタムハンドラ `_SSRFBlockRedirectHandler` を導入し、リダイレクト先のスキーム検証・プライベートアドレス（ループバック / リンクローカル等）へのアクセスを拒否。
    - フェッチ前にホストがプライベートかどうかを事前検査。
  - レスポンス保護:
    - 最大受信バイト数（10MB）を設定し、過大レスポンスを拒否（gzip 解凍後のサイズチェック含む）。
    - gzip 圧縮の安全な解凍とチェック。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去して URL を正規化。
    - 正規化後の URL の SHA-256 ハッシュ先頭32文字を記事IDとして使用し冪等性を実現。
  - テキスト前処理:
    - URL 除去、空白正規化、トリム処理を行う `preprocess_text` を実装。
  - DB 保存:
    - `save_raw_news` は INSERT ... ON CONFLICT DO NOTHING + RETURNING を用い、実際に挿入された記事IDを返却。チャンク単位（1000件）で一括挿入し、1 トランザクションにまとめる。
    - `save_news_symbols` / `_save_news_symbols_bulk` により記事と銘柄の紐付けを一括で保存（ON CONFLICT により重複はスキップ）。
  - 銘柄抽出:
    - テキストから 4 桁数字パターンを抽出し、与えられた known_codes のみにフィルタする `extract_stock_codes` 実装。
  - 統合ジョブ:
    - `run_news_collection` により複数 RSS ソースを順に取得・保存。ソース単位でエラーハンドリングし、1 ソースの失敗が他に影響しない設計。

- DuckDB スキーマ (`kabusys.data.schema`)
  - DataPlatform の 3 層構造に基づくテーブル設計を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約・CHECK・PRIMARY KEY・FOREIGN KEY を定義。
  - インデックスを頻出クエリパターンに合わせて作成。
  - `init_schema(db_path)` でファイルパスの親ディレクトリ自動作成と全DDL実行を行い、初回初期化を簡易化。
  - `get_connection(db_path)` で既存 DB への接続を取得するユーティリティを提供。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新ベースの ETL 実装を開始:
    - DB の最終取得日を検出し、未取得分のみを API から取得するロジック。
    - デフォルトのバックフィル日数を 3 日に設定し、後出し修正を吸収する設計。
    - 市場カレンダーは先読み（90 日）を行う構想（定数化済み）。
  - ETL 実行結果を格納する `ETLResult` データクラスを実装（品質問題・エラー情報を保持）。
  - ヘルパー関数:
    - テーブル存在チェック、最大日付取得、営業日調整（非営業日は直近の営業日に調整）などを提供。
  - 個別ジョブ: `run_prices_etl` を実装（差分取得、保存、ログ出力）。（他の ETL ジョブ雛形も含む設計）

### Changed
- 初回リリースのための設計ドキュメントに沿ったコード構成と API 設計を反映。
- 複数モジュールで DuckDB を標準永続層として採用（シンプルな SQL ベースの保存/更新処理を採用）。

### Fixed
- （初期リリース）主要なセキュリティ・信頼性上の注意点を実装時点で考慮済み:
  - defusedxml による XML パース、SSRF 防止、レスポンスサイズ制限、圧縮解凍後のサイズチェック、URL スキームの厳格化。

### Security
- ニュース収集に関して下記の対策を実装:
  - XML パースで defusedxml を使用（XML Bomb 対策）。
  - リダイレクト先のスキームチェックとプライベート IP 検査による SSRF 対策。
  - 受信データサイズ上限を設け、メモリ DoS を防止。
  - URL 正規化でトラッキングパラメータを除去し、同一記事の異なる URL による重複を防止。

### Known limitations / Notes
- ネットワークは同期的（urllib）で実装されているため、大量並列取得を行う用途では設計の見直しが必要になる可能性があります。
- ETL の品質チェックは別モジュール（kabusys.data.quality）を想定しているが、本差分には品質チェック本体の具体的実装が含まれていない場合があります（ETL 側は品質問題を集約できる設計）。
- 一部の低レベル I/O（例: news_collector._urlopen）はテスト用にモック可能な形で分離されています。
- 現在は主に日本株（4桁コード）向けのルールを採用。海外株式や別フォーマットの RSS への拡張は別途対応が必要。

---

今後の予定（例）
- ETL の残りジョブ（財務・カレンダーの差分ETL）の完成。
- quality モジュールによる自動品質判定とアラート連携。
- strategy / execution / monitoring モジュールの実装（注文実行、戦略評価、監視機能）。
- 非同期取得や並列化によるスケーラビリティ改善。

以上。