# Changelog

すべての重要な変更をここに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

※このファイルはコードベースから推測して生成した変更履歴です。

## [Unreleased]

（現在のリポジトリに未リリースの変更はありません。）

## [0.1.0] - 2026-03-17

初回公開リリース。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env.local は .env より優先して上書き。OS 環境変数は保護（上書き除外）。
  - .env パース機能:
    - コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応する堅牢なパーサを実装。
  - 必須設定取得用の _require() と以下のプロパティを提供:
    - J-Quants / kabuステーション / Slack / DB（DuckDB, SQLite）等の設定項目。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値チェック）。
  - 環境判定ヘルパー: is_live / is_paper / is_dev。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアント実装（株価日足、財務データ、マーケットカレンダーの取得）。
  - レート制限対応:
    - 固定間隔スロットリング（120 req/min 相当）を守る RateLimiter 実装。
  - 再試行（Retry）ロジック:
    - 指数バックオフ、最大試行回数 3 回。
    - HTTP 408/429/5xx に対するリトライ。
    - 429 の場合は Retry-After を優先。
  - 認証トークン管理:
    - refresh token から id_token を取得する get_id_token。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止する設計）。
    - モジュールレベルでのトークンキャッシュ（ページング間で共有）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - ページネーションキーの重複検出でループを終了。
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
    - PK 欠損レコードのスキップとログ出力、保存件数のログ記録。
  - データ型変換ユーティリティ:
    - _to_float / _to_int（厳密な変換ルール、例: 小数部がある数値文字列は int へ変換しない）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集と raw_news への保存ワークフローを実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検証、ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否。
    - 許可スキームは http/https のみ。
    - レスポンスの最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - User-Agent、Accept-Encoding の設定。
  - URL 正規化・記事ID生成:
    - トラッキングパラメータ（utm_* 等）除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去。
    - 正規化後の SHA-256（先頭32文字）を記事IDに採用し冪等性を保証。
  - テキスト前処理:
    - URL 除去、空白の正規化、先頭末尾トリム。
  - RSS パースのフォールバック（channel がないフィードへの対応）と pubDate の RFC2822 パース（タイムゾーン標準化）。
  - DB への効率的保存:
    - save_raw_news: チャンク挿入、INSERT ... RETURNING id で新規挿入IDを取得、トランザクションでまとめてコミット。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入、重複除去、チャンク処理、INSERT ... RETURNING を利用し挿入数を正確に返す。
  - 銘柄抽出:
    - 正規表現に基づく 4 桁コード抽出（既知コードセットとの照合でフィルタ、重複排除）。
  - 統合ジョブ run_news_collection:
    - 複数 RSS ソースの順次処理、ソース単位でのエラーハンドリング（1ソース失敗しても残り継続）。
    - 新規挿入記事のみを対象に銘柄紐付けを行う。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - データプラットフォームの 3 層（Raw / Processed / Feature）と Execution 層を含むテーブル群を定義。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（PRIMARY KEY / FOREIGN KEY / CHECK）を付与。
  - インデックスの定義（頻出クエリ向け: code×date、ステータス検索など）。
  - init_schema(db_path) によりディレクトリ作成も含めて冪等に初期化可能。
  - get_connection() による既存 DB への接続。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を中心とした ETL 設計。
  - 機能:
    - 最終取得日の照会（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 営業日調整ヘルパー _adjust_to_trading_day（market_calendar に基づく調整、最大 30 日遡る）。
    - run_prices_etl: 差分取得（date_from 自動計算、バックフィル日数の指定により後出し修正を吸収）、jquants_client の fetch/save を利用して取得→保存を実行。
  - ETL 実行結果を格納する ETLResult dataclass を追加:
    - 取得件数・保存件数、品質チェック結果リスト、エラーリスト等を集約。
    - has_errors / has_quality_errors / to_dict を提供。
  - 品質チェックモジュール quality との連携を想定（quality.QualityIssue を参照）。

### 変更 (Changed)
- 初期リリースにつき無し。

### 修正 (Fixed)
- 初期リリースにつき無し。

### セキュリティ (Security)
- ニュース収集モジュールに複数の SSRF / XML / DoS 対策を実装:
  - defusedxml を採用した XML パース、安全でないスキーム/プライベートアドレスの拒否、レスポンスサイズ上限、gzip 解凍後のサイズチェック、リダイレクト検査。
- .env パースでエスケープ処理やクォート処理を適切に扱うことで注入/パースの脆弱性を軽減。

### パフォーマンス (Performance)
- J-Quants 呼び出しに RateLimiter を導入し API レートを厳守。
- ニュース/紐付けの DB 挿入をチャンク化してトランザクションをまとめ、オーバーヘッドを低減。
- INSERT ... RETURNING を活用して実際に挿入された件数を正確に把握。

### 既知の注意点 / マイグレーション
- init_schema() は既存テーブルが存在する場合はスキップするため、既存DBに対して安全に呼び出せます。
- .env 自動ロードはプロジェクトルート探索を行うため、配布後に想定外の挙動になる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- quality モジュールは pipeline 内で参照されていますが（ETLResult 等）、このリリース内に quality の実装ファイルは含まれていない場合があります（外部実装または別モジュールとして提供される想定）。

---

詳細な実装・設計方針は各モジュールの docstring とコードコメント（src/kabusys/data/*.py, src/kabusys/config.py, src/kabusys/data/schema.py 等）を参照してください。