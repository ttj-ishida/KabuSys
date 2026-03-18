# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを初期リリース。パッケージバージョンは 0.1.0（src/kabusys/__init__.py）。
  - サブパッケージ構成（data, strategy, execution, monitoring）を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env および環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env 行パーサ実装（export プレフィックス、クォート、インラインコメント、エスケープ対応）。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - J-Quants / kabu API / Slack トークン関連（必須チェックを行い未設定時は例外を送出）
    - データベースパス（DuckDB / SQLite）、環境種別（development/paper_trading/live）、ログレベル等の取得ヘルパ。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - ID トークン取得（get_id_token）とキャッシュ機構（モジュールレベルキャッシュ）。
  - API 呼び出し共通関数 _request を実装。機能:
    - 固定レートのスロットリング（120 req/min 固定間隔）を内蔵する RateLimiter。
    - リトライ（指数バックオフ、最大 3 回）。対象ステータス: 408/429/5xx。429 時は Retry-After を考慮。
    - 401 受信時は自動的にリフレッシュし1回リトライ（無限再帰を防止）。
    - JSON デコードのエラーハンドリング。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等設計: INSERT ... ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ取得時の fetched_at（UTC）記録により、データが「いつ知り得たか」を追跡可能に。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得・解析と raw_news への保存機能を実装。
  - 主要機能:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保
    - defusedxml を使用した XML パース（XML Bomb 対策）
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキームとホスト検証、プライベート IP 判定
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）
    - テキスト前処理（URL 除去、空白正規化）
    - DuckDB への一括保存（チャンク化、トランザクション、INSERT ... RETURNING による新規件数取得）
    - 銘柄コード抽出（4桁数字、既知コードセットとの照合）と news_symbols への一括保存
  - デフォルト RSS ソース: Yahoo Finance（business カテゴリ）が設定される。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md の設計を反映したスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）や推奨インデックスを定義。
  - init_schema(db_path) で DB ファイル親ディレクトリ作成 → テーブル/インデックス作成を行う（冪等）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を中心とした ETL 設計を実装するための基盤実装。
  - ETLResult dataclass を提供（取得数・保存数・品質チェック結果・エラー一覧等を保持）。
  - テーブル存在チェック、最大日付取得ユーティリティの実装。
  - 市場カレンダーを考慮した営業日調整ヘルパ（_adjust_to_trading_day）。
  - 差分更新ヘルパ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl を実装（差分算出、backfill_days による再取得、jquants_client の fetch/save を利用）。
  - 品質チェックモジュール（quality）と連携する設計（品質問題は収集を止めず呼び出し元が対処可能）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector における SSRF 対策を実装:
  - リダイレクト時にスキームとホストを検査するカスタム RedirectHandler を使用。
  - プライベート/ループバック/リンクローカル/マルチキャストアドレス判定を行い、内部アドレスへのアクセスを拒否。
  - defusedxml により XML に起因する攻撃を軽減。
  - レスポンスボディの最大バイト数チェックと gzip 解凍後の再チェックでメモリ DoS を防止。

### 既知の問題・制約 (Known issues / Limitations)
- run_prices_etl の戻り値の不整合:
  - 関数シグネチャは (int, int) を返すことを想定しているが、実装末尾にある return 文が不完全（ソースでは "return len(records), " のようになっており、実際には 1 要素のタプルしか返さない可能性がある）。呼び出し側で期待される型と一致しないため要修正。
- DNS 解決失敗時の扱い:
  - _is_private_host は DNS 解決に失敗した場合に「非プライベート」とみなして続行する設計。環境によってはこれがリスクとなる可能性があり、運用環境に応じた挙動検討が必要。
- ネットワーク同期 I/O:
  - HTTP クライアント実装は urllib を使用する同期処理。大量並列フェッチ等のユースケースでは非同期実装やワーカー設計の検討が必要。
- 外部モジュール依存:
  - quality モジュールは参照されているが本リリース内に未含の場合、品質チェック連携部分は未完成または外部提供が必要。
- テストフック:
  - fetch_rss 内の _urlopen はテストでモック可能だが、外部ネットワークに依存する箇所は統合テスト実行時に注意が必要。

### 補足 (Notes)
- 多くの処理において「冪等性（idempotency）」を重視した設計を採用（DB 側の ON CONFLICT / DO UPDATE、記事 ID のハッシュ化など）。
- データ取得時に fetched_at を記録することで、将来的なデータのタイムライン監査（Look-ahead bias の回避）をサポート。

---

本 CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノートや運用ポリシーに合わせて表現・項目を調整してください。必要であれば、各変更項目に対応するイシュー番号やコミットハッシュを追加します。