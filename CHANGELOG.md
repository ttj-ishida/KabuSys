# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はコードベースの現在日付（`__version__ = "0.1.0"`）に基づいて記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。主な追加点・設計方針は以下のとおりです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - パッケージの公開 API を `__all__` で定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env 解析の強化:
    - export 形式やクォート内のエスケープ、インラインコメントの扱いに対応。
  - 必須環境変数取得ヘルパー（未設定時は ValueError を送出）。
  - Settings クラスを提供し、以下の項目をプロパティとして取得:
    - J-Quants API: JQUANTS_REFRESH_TOKEN
    - kabuステーション API: KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH (default data/kabusys.duckdb), SQLITE_PATH (default data/monitoring.db)
    - 環境種別判定: KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL 検証
    - is_live / is_paper / is_dev ヘルパー

- データ層：J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守（RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス (408, 429, 5xx)。
  - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回だけリトライ。
  - ページネーション対応（pagination_key を利用し重複防止）。
  - データ取得時に fetched_at を UTC タイムスタンプで記録して Look-ahead Bias を防止。
  - DuckDB への保存関数は冪等性を確保（ON CONFLICT DO UPDATE）:
    - save_daily_quotes: raw_prices テーブルに保存（PK: date, code）
    - save_financial_statements: raw_financials に保存（PK: code, report_date, period_type）
    - save_market_calendar: market_calendar に保存（PK: date）
  - 型変換ユーティリティ (_to_float, _to_int) を実装し不正値を安全に扱う。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集機能を実装。
  - 設計・実装の主要点:
    - デフォルトRSS: Yahoo Finance ビジネスカテゴリを登録。
    - 記事ID は URL 正規化後の SHA-256（先頭32文字）で生成して冪等性保証（utm_* 等のトラッキングパラメータを除去）。
    - XML パースに defusedxml を使用し XML Bomb 等の脅威を低減。
    - SSRF 対策:
      - リダイレクト時にスキーム検証とプライベートアドレス検査を行うカスタム RedirectHandler (_SSRFBlockRedirectHandler) を導入。
      - 初回リクエスト前にホストがプライベートか検査して拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査でメモリ DoS を防止。
    - 非 http/https スキームの URL を排除。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存はトランザクションでまとめ、チャンク分割して INSERT … RETURNING を使用:
      - save_raw_news: raw_news テーブルに挿入し、実際に挿入された記事IDのリストを返す（ON CONFLICT DO NOTHING）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ（news_id, code）ペアを一括保存し挿入数を正確に返す。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes に含まれるもののみ採用（重複除去）。

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform 設計に基づく包括的スキーマを追加。
  - レイヤー:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する制約（CHECK, PRIMARY KEY, FOREIGN KEY）や適切なデータ型を定義。
  - 頻出クエリ用のインデックスを作成。
  - init_schema(db_path) を提供し、DB ファイル親ディレクトリの自動作成とテーブル初期化を行う（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新に基づく ETL ヘルパーとジョブ基盤を実装。
  - 設計方針:
    - 差分更新デフォルト単位は営業日 1 日分。
    - backfill_days により最終取得日から数日前を再取得して API の後出し修正を吸収。
    - 品質チェック（quality モジュール想定）で検出された問題は収集を継続し呼び出し元で対応可能にする（Fail-Fast ではない）。
    - id_token を引数注入できる設計でテスト容易性を確保。
  - ETLResult データクラスを提供し、実行結果（取得数、保存数、品質問題、エラー等）を集約して出力可能。
  - テーブル存在確認・最大日付取得ユーティリティ、取引日補正ヘルパーを実装。
  - run_prices_etl をはじめとする差分 ETL の骨組みを実装（fetch → save の流れ）。

### セキュリティ (Security)
- XML パースに defusedxml を利用して XML ベースの攻撃を低減。
- RSS フェッチでの SSRF 対策:
  - リダイレクト時にスキーム検証／ホストのプライベートアドレス検査を行う。
  - 初回リクエスト前にもホストのプライベート判定を行う。
- レスポンス受信時のバイト数上限や gzip 解凍後のサイズチェックを導入して Gzip Bomb / メモリ枯渇攻撃に耐性を持たせる。
- .env 読み込み時に OS 環境変数を保護するための protected キー制御を実装。

### その他 (Notes)
- J-Quants API のレート制御は _MIN_INTERVAL_SEC = 60 / 120（120 req/min）で固定間隔スロットリング方式を採用。
- retry: 最大 3 回の再試行、429 用に Retry-After ヘッダーを優先、指数バックオフを採用。
- ID トークンの自動リフレッシュは 401 発生時に最大 1 回実行し、それでも 401 の場合は即失敗する設計。
- DB 初期化は init_schema() を必ず初回に呼び出すこと（get_connection はスキーマを作成しない）。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD）が未設定の場合、Settings のプロパティ呼び出しで ValueError が発生します。
- デフォルトの DuckDB パスは data/kabusys.duckdb（必要に応じて DUCKDB_PATH で上書き）。

### 既知の制限 (Known issues / TODO)
- quality モジュールの具体的実装は想定されている（pipeline と ETLResult は quality.QualityIssue に依存）。
- strategy, execution, monitoring パッケージの本体はスケルトン（モジュール __init__ のみ）であり、具体的戦略ロジック・発注ロジックは未実装。
- 一部関数（例: run_prices_etl の戻り値処理）の続き実装がファイル終端で切れているため、ETL フローの最終整備が必要。

### 変更点 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

---

必要があれば、各モジュールごとの API 仕様（関数シグネチャ、期待される例外、サンプル使用方法）や初期セットアップ手順（必須環境変数一覧、DB 初期化コマンド例）を別途ドキュメント化します。どの情報が必要か教えてください。