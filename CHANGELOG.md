# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  
安定版リリースのフォーマット: [version] - YYYY-MM-DD

※本CHANGELOGはリポジトリ内のソースコードから機能・設計を推測して作成しています。

## [Unreleased]

（なし）


## [0.1.0] - 2026-03-17
初回公開リリース

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定・管理
  - 環境変数読み込みモジュールを追加（kabusys.config）。
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を基準）を実装し、カレントワーキングディレクトリに依存しない自動 .env 読み込みを提供。
  - .env/.env.local の自動読み込み（OS 環境変数を保護する protected ロジック、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env のパース機能を強化（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の取得とバリデーションを実装。

- J-Quants API クライアント
  - jquants_client モジュールを追加（データ取得と保存のユーティリティ）。
  - 取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - 設計的特徴:
    - レートリミッタ実装（固定間隔スロットリング、デフォルト 120 req/min を厳守）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象、429 の場合は Retry-After ヘッダ優先）。
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライ（無限再帰防止フラグあり）。
    - ページネーション対応（pagination_key を用いて全ページ取得）。
    - データ取得時に fetched_at を UTC で記録し、Look-ahead Bias の追跡を容易に。
  - DuckDB への保存関数（冪等性確保）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 各関数は ON CONFLICT DO UPDATE を用いて重複を更新（冪等操作）。
    - PK 欠損行はスキップしログに警告を出力。

- ニュース収集モジュール
  - news_collector を追加（RSS フィードからニュースを収集して raw_news に保存）。
  - 主な機能:
    - RSS 取得・XML パース（defusedxml を使用して XML による脆弱性対策）。
    - コンテンツ前処理（URL 除去、空白正規化）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証（utm_* 等のトラッキングパラメータ除去）。
    - HTTP/HTTPS スキーム検証、リダイレクト時のスキーム/ホスト検査（SSRF 対策用カスタムリダイレクトハンドラ）。
    - レスポンスサイズ制限（デフォルト 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - DB 保存はチャンク化・トランザクション化（INSERT ... RETURNING を使って実際に挿入された ID を取得）。
    - 銘柄コード抽出機能（4桁の数字候補から known_codes と照合して抽出）。
    - run_news_collection により複数 RSS ソースを順次処理し、新規記事・銘柄紐付けを行う。

- DuckDB スキーマ定義と初期化
  - schema モジュールを追加。DataSchema.md に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル・インデックス作成を行い、冪等に初期化できる。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン
  - pipeline モジュールを追加。差分更新・バックフィル・品質チェック連携を想定した ETL ワークフローを実装。
  - 主な機能:
    - 差分更新のヘルパー（DB の最終取得日取得関数: get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 営業日調整ヘルパー（market_calendar を参照して非営業日を直近営業日に調整）。
    - run_prices_etl（株価差分 ETL）の雛形（date_from 自動算出、バックフィル日数の取り扱い、fetch → save のフロー）。
    - ETL 実行結果を表す ETLResult データクラス（品質問題・エラー一覧・集計値を保持）。

- ユーティリティ
  - 型安全な変換関数: _to_float / _to_int（空値・不正値は None、float 表現からの整数変換は小数部が非ゼロなら None を返す等の挙動を明示）。
  - RSS 解析の日時パース関数（RFC2822 形式を UTC naive に正規化、失敗時は警告ログと現在時刻で代替）。
  - ネットワーク呼び出しのテスト容易性考慮（news_collector._urlopen をモック置換可能）。

### Security
- セキュリティ対策を多数組み込み
  - RSS XML のパースに defusedxml を使用して XML 関連の脆弱性を低減。
  - SSRF 対策:
    - 取得前にホストのプライベート/ループバック/リンクローカル判定を行い内部アドレスアクセスを拒否。
    - リダイレクト時にスキームとホストを検査する専用 RedirectHandler を実装。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）や gzip 解凍後のサイズ再検査で DoS 対策。
  - .env パースで安全な取り扱い（エスケープやクォート処理）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Breaking Changes
- （初版のため該当なし）

### Notes / Implementation details
- jquants_client の _request は内部で id_token キャッシュを保持。get_id_token は refresh_token を settings から取得可能。
- news_collector は既定の RSS ソースとして Yahoo Finance のビジネスカテゴリを追加（DEFAULT_RSS_SOURCES）。
- DB への保存関数は可能な限り冪等に設計（ON CONFLICT DO UPDATE / DO NOTHING を活用）。
- ETL の品質チェック連携（quality モジュール）は、重大度の異なる問題を収集しつつ ETL 自体は継続する設計（Fail-Fast ではない）。

---

（以降のリリースでは、各項目をカテゴリ別に時系列で追記してください）