# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリースノートは日本語で記載しています。

- リリースポリシー: ここではリポジトリ内の現状コードベースから推測される初期リリース内容を記載しています。

## [Unreleased]

（現状なし）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基本モジュールを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して判定（CWD 非依存）。
  - .env のパース: export 形式、シングル/ダブルクォート、インラインコメント、エスケープに対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化のための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等をプロパティで取得可能に。
  - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の値検証。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本 API エンドポイントラッパーを実装（/prices/daily_quotes、/fins/statements、/markets/trading_calendar 等）。
  - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - 再試行/リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx 対応。429 の場合は Retry-After ヘッダを優先。
  - 401 (Unauthorized) を受けた場合は自動でリフレッシュを行い 1 回のみ再試行（無限再帰を防止）。
  - トークンキャッシュをモジュールレベルで保持し、ページネーションや複数呼び出しで共有。
  - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装（ページネーション対応）。
  - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar を実装。fetched_at を UTC で記録し、ON CONFLICT DO UPDATE により冪等性を担保。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得・前処理・DuckDB へ保存する一連処理を実装。
  - デフォルト RSS ソースに Yahoo Finance (business) を追加。
  - セキュリティ・堅牢性対策:
    - defusedxml を使用して XML Bomb 等の攻撃を緩和。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことをチェック、リダイレクト時にも検査するカスタム RedirectHandler を実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズチェック（Gzip-bomb対策）。
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化。
  - 記事 ID: 正規化 URL の SHA-256 ハッシュ先頭 32 文字を使用し冪等性を保証。
  - テキスト前処理: URL 除去・空白正規化を実施。
  - DB 保存:
    - save_raw_news はチャンク分割（_INSERT_CHUNK_SIZE）およびトランザクション管理を行い、INSERT ... ON CONFLICT DO NOTHING RETURNING で実際に挿入された記事 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けを一括保存（INSERT ... RETURNING）し、重複除去を行う。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes によるフィルタリングを実施。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーを想定したテーブル群を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の生データテーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の整形済みテーブルを定義。
  - features, ai_scores など特徴量テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など実行・ポートフォリオ管理テーブルを定義。
  - 頻出クエリ用のインデックスを複数定義。
  - init_schema(db_path) でディレクトリ作成（必要時）と DDL 実行を行い、初期化済み DuckDB 接続を返す。get_connection(db_path) で接続のみ取得可能。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、ETL 実行結果・品質チェック結果・エラーを集約して返却可能に。
  - 差分更新ロジックのユーティリティを実装（テーブル存在チェック、最終取得日の取得）。
  - 市場カレンダーの「営業日調整」ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl をはじめとした個別 ETL ジョブの骨組み（差分取得、backfill のデフォルト 3 日、最小データ日付の設定等）を実装。
  - ETL の設計方針として、品質チェックでエラーがあっても ETL を継続する（Fail-Fast ではない設計）点を明記。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Security
- news_collector:
  - defusedxml による XML パース、防御的なリダイレクト検査、プライベートアドレス検査、受信バイト制限、gzip 解凍後のサイズ検査など多層防御を導入。
- jquants_client:
  - 認証トークンの自動リフレッシュ時に無限再帰を防止する仕組みを実装。

### Deprecated
- （初版につき該当なし）

### Removed
- （初版につき該当なし）

### Notes / Known design points
- 設定の自動 .env ロードはプロジェクトルートの検出に依存するため、配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御可能。
- DuckDB への INSERT は各 save_* 関数で ON CONFLICT を利用して冪等性を確保。
- ニュース記事 ID は URL 正規化とトラッキングパラメータの除去に依存するため、ソースフィードの仕様変更により重複/漏れの可能性がある点に留意。
- ETL パイプラインは品質チェックモジュール（kabusys.data.quality）と連携する設計が前提。品質チェックは重大度を持つ問題を検出しても ETL を即停止しない（呼び出し側が方針を決定）。

---

今後のリリースでは、strategy / execution / monitoring モジュールの実装拡充、テストカバレッジの追加、運用向けの監視・アラート整備、ドキュメント（DataPlatform.md / DataSchema.md 等）の整備・同期を予定しています。