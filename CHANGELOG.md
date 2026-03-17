# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要コンポーネントと機能を含みます。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダー実装
    - 読み込み順: OS環境 > .env.local > .env
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、インラインコメント、バックスラッシュエスケープに対応
  - 保護された OS 環境変数を上書きから除外する仕組み
  - Settings クラスを提供（プロパティ経由で以下を取得）
    - J-Quants リフレッシュトークン / Kabu API パスワード / Kabu API ベース URL
    - Slack トークン・チャネル ID
    - データベースパス（DuckDB/SQLite の既定値あり）
    - 実行環境（development / paper_trading / live）の検証
    - ログレベルの検証

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出し用ユーティリティ（JSON デコード、エラーハンドリング）
  - レート制御: 固定間隔スロットリング（デフォルト 120 req/min を尊重）
  - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を再試行対象
  - 401 応答時の自動トークンリフレッシュ（1 回）
  - token キャッシュとページネーションを考慮したトークン共有
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性を担保）
    - save_daily_quotes（raw_prices、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT DO UPDATE）
  - データ品質のための fetched_at（UTC ISO 形式）を記録
  - ユーティリティ関数: 安全な数値変換 (_to_float, _to_int)

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集パイプライン実装
    - デフォルトソース（Yahoo Finance Business RSS）を含む
  - セキュリティと堅牢性:
    - defusedxml による XML パース（XML-Bomb 等対策）
    - HTTP リダイレクト時の事前検証ハンドラで SSRF を防止
    - URL スキーム検証（http/https のみ許可）
    - ホスト/IP のプライベート判定（DNS 解決して A/AAAA を検査）
    - レスポンスサイズ上限（10 MB）と gzip 解凍後の再チェック
    - User-Agent と Accept-Encoding の設定
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保
  - URL 正規化: トラッキングパラメータ（utm_* 等）除去、クエリソート、フラグメント削除
  - テキスト前処理（URL 除去・空白正規化）
  - DuckDB への保存:
    - save_raw_news: INSERT ... RETURNING id を用いて新規挿入IDのリストを返す。チャンク + 単一トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、RETURNING を利用）
  - 銘柄コード抽出: 4桁数字を抽出し、与えられた known_codes セットでフィルタ

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層 + 実行層のテーブル定義を実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（CHECK, PRIMARY KEY, FOREIGN KEY）を多数設定
  - 頻出クエリ用のインデックスを作成
  - init_schema(db_path) で親ディレクトリを自動作成してスキーマ初期化
  - get_connection(db_path) を提供（初期化を行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラス（品質問題、エラー、取得/保存数を含む）
  - 差分更新ロジック:
    - DB の最終取得日を基に自動で date_from を決定（デフォルトバックフィル 3 日）
    - 市場カレンダーの先読み（デフォルト 90 日）を考慮する設計
  - ヘルパー関数:
    - テーブル存在判定、最大日付取得、営業日に調整する _adjust_to_trading_day
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl: 差分取得 → 保存（jquants_client の save_* を利用）を行うジョブ（テスト可能な id_token 注入対応）

### 変更 (Changed)
- （初回リリースにつき、履歴上の過去変更は無し）

### 修正 (Fixed)
- （初回リリースにつき、過去バグ修正は無し）

### セキュリティ (Security)
- RSS パーサーに defusedxml を導入し、リダイレクト検証・プライベートIP検査・スキーム検証を組み合わせて SSRF を強く抑制
- .env パーサーはクォート内のバックスラッシュエスケープを正しく扱うことで誤解析を低減

### 既知の問題 (Known issues)
- run_prices_etl 関数の末尾の return 文が不完全（現行コードは `return len(records), ` のように見え、保存件数を返す tuple が未完成）です。ETL の呼び出し側は現在の戻り値仕様（取得数, 保存数）を期待するため、ここは修正が必要です（保存数を返すように return を修正してください）。
- 一部のネットワークエラーや HTTPError の場合、最終例外を内包して RuntimeError を投げます。呼び出し側で詳細原因をログに残す運用を推奨します。
- news_collector では DNS 解決失敗時に安全側（非プライベート）とみなす実装のため、特殊な DNS/TLS 環境では想定外のホストへ接続し得る点に注意してください。

### マイグレーション / 運用上の注意 (Notes)
- デフォルトの DuckDB ファイルパスは data/kabusys.duckdb（Settings.duckdb_path）です。運用環境では適切な永続領域を指定してください。
- .env.example を用意し、必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。Settings._require は未設定時に ValueError を投げます。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途を想定）。
- DB の初回セットアップは init_schema(db_path) を呼ぶことで行えます。既存テーブルはスキップされるため安全に再実行できます。

---

開発・利用に関する問い合わせやバグ報告はリポジトリの Issues へお願いします。