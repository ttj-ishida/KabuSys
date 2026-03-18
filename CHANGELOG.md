# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って管理しています。

フォーマット:
- Unreleased: 次リリースに向けた未リリースの変更（現在は空またはノート）
- 各バージョン: 変更点をカテゴリ別（Added, Changed, Fixed, Security など）で記載

## [Unreleased]
- 今後の予定メモ:
  - strategy / execution / monitoring パッケージの具現化（現在はパッケージ初期化ファイルのみ）
  - quality チェックの詳細実装と ETL の品質検出フロー強化
  - パイプラインの追加エンドポイント（run_prices_etl の戻り値/例外処理整備など）

---

## [0.1.0] - 2026-03-18
初回公開リリース — 日本株自動売買システムの基盤機能を実装。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py にてパッケージ名とバージョンを定義（バージョン: 0.1.0）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（各サブパッケージを公開）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD 非依存で自動ロード。
  - .env と .env.local の読み込み優先順位（OS 環境変数を保護する protected 機構含む）。
  - .env パースの強化:
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応と、インラインコメントの無視。
    - クォート無し値のインラインコメント取り扱いの明確化。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応（テスト用）。
  - settings クラスに各種設定プロパティを用意（J-Quants トークン、kabuAPI, Slack, DBパス、環境/ログレベル判定など）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）とヘルパープロパティ（is_live / is_paper / is_dev）。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API クライアント実装（/prices/daily_quotes、/fins/statements、/markets/trading_calendar 等）。
  - レートリミッタ（固定間隔スロットリング）: 120 req/min を守る実装。
  - 冪等な DuckDB 保存用ヘルパ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE を使用）。
  - HTTP リクエストに対するリトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ保証）による再試行。
  - ページネーション対応（pagination_key の共有・ループ防止）。
  - データ取得時の fetched_at を UTC で記録し、Look-ahead Bias を抑制。
  - 型安全なユーティリティ (_to_float, _to_int) によるデータ正規化。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集機能を実装（デフォルトソースに Yahoo Finance のビジネス RSS を含む）。
  - セキュアな XML パース（defusedxml）を採用し XML Bomb 等の攻撃を低減。
  - SSRF 対策:
    - リダイレクト事前検査ハンドラ（_SSRFBlockRedirectHandler）でスキームとプライベートアドレスをチェック。
    - 初回 URL と最終 URL の両方でスキーム検証とプライベートホストチェックを実施。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化:
    - スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリキーソートなど。
    - 正規化 URL から SHA-256 の先頭 32 文字を記事IDとして生成（冪等性の確保）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - raw_news へのチャンク挿入と INSERT ... RETURNING による実際に挿入された ID の取得。
    - news_symbols（記事-銘柄紐付け）へのバルク挿入（重複除去、チャンク、トランザクション）。
  - 銘柄コード抽出ユーティリティ（4桁数値の抽出と known_codes によるフィルタリング）。
  - run_news_collection：複数ソースを巡回し個別にエラーハンドリングして DB に保存・銘柄紐付けを行う統合ジョブ。

- スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution の 3 層＋実行層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores などの Feature レイヤーテーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_* など実行管理テーブルを定義。
  - 頻出クエリに備えたインデックスを追加。
  - init_schema(db_path) により DB ファイル親ディレクトリの自動作成とテーブル作成を行う冪等な初期化機能を提供。
  - get_connection(db_path) による既存 DB への接続ヘルパを提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計に基づき、差分更新・バックフィル・品質チェックの基本構成を実装。
  - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー等の集約）。
  - テーブル存在チェック、最終取得日取得ユーティリティを実装（get_last_price_date 等）。
  - 市場カレンダーを参照して営業日に調整する _adjust_to_trading_day を実装。
  - run_prices_etl の骨組みを実装（差分計算、fetch -> save の流れ）。backfill_days による後出し修正吸収方針を採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS/XML パースに defusedxml を利用し、外部エンティティ／XML Bomb を軽減。
- HTTP リダイレクトでの SSRF 対策（スキーム検証、プライベートIP/ホスト検出）。
- .env ファイル読み込み時に OS 環境変数を保護する protected 機構を導入。
- ニュース取得で Content-Length/読み取り上限をチェックすることでメモリDoSを軽減。

### Notes / Known limitations
- strategy, execution, monitoring パッケージは現状で初期化モジュールのみ（実装は今後）。
- quality モジュールは参照されているが詳細チェックロジックは別途実装が必要（ETL パイプラインは品質問題を収集する設計）。
- J-Quants クライアントはネットワーク／API 側のエラーに対してリトライを行うが、環境依存の例外ケースは運用での監視が必要。
- run_prices_etl 等パイプラインの公開 API は今後の拡張（ログ・監査・より細かなエラーハンドリング）を予定。

---

作成者注: 上記はリポジトリ内コードの実装内容から推測して作成した CHANGELOG です。実際のリリースノートや日付・バージョン付けはプロジェクト運用方針に合わせて調整してください。