# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

※この CHANGELOG はリポジトリ内のコードから推測して作成しています。

## [Unreleased]
- 次期リリース向けの変更や未確定の修正をここに記載します。

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームのコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン情報と公開モジュールを定義。
  - モジュール構成: data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ローダを実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - プロジェクトルート検出 (.git または pyproject.toml を起点) による堅牢な .env 検出。
  - .env 解析機能:
    - export KEY=val 形式対応、シングル/ダブルクォート処理、バックスラッシュエスケープ、行内コメント扱い。
    - override / protected キー機能により OS 環境変数の保護をサポート。
  - Settings クラスでアプリ設定を型付きプロパティとして公開（J-Quants トークン、kabu API、Slack、DB パス、環境判定、ログレベル等）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - /token/auth_refresh による ID トークン取得関数 get_id_token を実装。
  - 株価日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、JPX カレンダー（fetch_market_calendar）を取得する API 呼び出しを実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ、最大 3 回、ネットワーク系/429/5xx をリトライ対象に設定。429 の場合は Retry-After ヘッダを尊重。
  - 401 受信時にはトークンを自動リフレッシュして 1 回だけ再試行する仕組み（無限再帰防止）。
  - モジュールレベルの ID トークンキャッシュを導入し、ページネーションや複数リクエストでトークンを共有。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
  - データ変換ユーティリティ (_to_float / _to_int) を実装し、不正値や空値を安全に扱う。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得し raw_news に保存する機能を実装（fetch_rss / save_raw_news / run_news_collection 等）。
  - セキュリティおよび頑健性:
    - defusedxml を用いた XML パース（XML Bomb 等への対処）。
    - HTTP/HTTPS スキームのみ許可し、SSRF 対策を強化するホスト/IP のプライベートアドレス判定。
    - リダイレクト時にスキームとホストを検証するカスタム HTTPRedirectHandler を導入。
    - 最大受信バイト数（MAX_RESPONSE_BYTES = 10 MB）で読み込みを制限、gzip 対応かつ解凍後サイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去（utm_*, fbclid 等）と URL 正規化。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - DB 処理:
    - INSERT ... RETURNING を利用して実際に挿入された件数/ID を正確に取得。
    - バルク INSERT はチャンク化して一括トランザクションで実行（チャンクサイズ制御）。
    - news_symbols による記事と銘柄コードの紐付け関数を実装（重複除去・トランザクション）。
  - テキスト前処理（URL除去・空白正規化）と RSS pubDate の堅牢なパース（UTC 正規化）、失敗時は現在時刻で代替。
  - 銘柄コード抽出ロジック（4桁数字パターン + known_codes フィルタ）を実装。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層（正確には Raw / Processed / Feature / Execution の 4 層）に対応するテーブル群を DDL として定義。
  - テーブル群:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約や CHECK、PRIMARY KEY、外部キー、インデックスを含む設計（データ整合性とクエリ性能を考慮）。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行を行い、冪等にスキーマを初期化する API を提供。get_connection() も提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新/バックフィルを意識した ETL ヘルパー群を実装:
    - 現在の最終取得日取得関数 (get_last_price_date / get_last_financial_date / get_last_calendar_date)。
    - 営業日調整ヘルパー (_adjust_to_trading_day)。
    - run_prices_etl 等の個別 ETL ジョブ（差分取得、backfill_days による再取得）。
  - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラーを集約して返却。品質チェック結果のシリアライズ機能あり。
  - 品質チェック（quality モジュール想定）との連携を想定した設計（品質問題は一覧化して呼び出し元で処理）。

### 変更 (Changed)
- （初回公開のため該当なし）

### 修正 (Fixed)
- （初回公開のため該当なし）

### セキュリティ (Security)
- RSS 処理における SSRF / XML 攻撃対策を実装（プライベートアドレス判定、リダイレクト時検証、defusedxml、受信サイズ制限、Gzip 解凍後サイズチェック）。
- .env ロード時に OS 環境変数を保護する protected 機構を実装。

### パフォーマンス (Performance)
- J-Quants API へのレート制御と再試行ロジックにより安定性向上。
- ニュース収集のバルクインサートをチャンク化してトランザクションをまとめることで DB オーバーヘッドを低減。
- DuckDB 用に頻出クエリ用のインデックスを作成。

### 内部 (Internal)
- 各モジュールはテスト可能なようにトークン注入・urlopen の差し替えポイントを用意（依存注入でモック可能）。
- 例外とログ出力を適切に分離し、障害時の原因追跡を容易にする設計。
- 型注釈（PEP 484/Type hints）を多用し、静的解析・テストのしやすさを配慮。

---

参考:
- この CHANGELOG はリポジトリ内のコード実装から機能を推測して作成しています。実際のリリースノートはプロダクトオーナーの判断で調整してください。