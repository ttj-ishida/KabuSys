# CHANGELOG

すべての変更は "Keep a Changelog" の形式に従い、重要度別に分類しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買基盤のコア機能を実装しました。主要な追加点と設計上のポイントは以下の通りです。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。
  - サブモジュール構成: data, strategy, execution, monitoring を公開。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行い、CWD に依存しない実装。
  - .env と .env.local の優先順位を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - export KEY=val 形式やクォート・インラインコメントに対応したパーサを実装。
  - Settings クラスを提供し、J-Quants、kabuステーション、Slack、DB パス、環境（development/paper_trading/live）、ログレベル等をプロパティとして取得可能。
  - 必須環境変数未設定時は ValueError を送出する require ロジックを実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得 API を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
  - 401 受信時にリフレッシュトークンから自動で id_token を更新して 1 回リトライする仕組み（キャッシュ付き）。
  - ページネーション対応（pagination_key を使用した繰り返し取得）。
  - データ取得時に fetched_at（UTC）を付与して Look-ahead Bias 対策。
  - DuckDB への保存関数を idempotent に実装（ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes: raw_prices テーブルへの保存（PK: date, code）。
    - save_financial_statements: raw_financials テーブルへの保存（PK: code, report_date, period_type）。
    - save_market_calendar: market_calendar テーブルへの保存（PK: date）。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正データを安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集し raw_news に保存する機能を実装。
  - 記事IDは URL 正規化後の SHA-256 の先頭 32 文字で生成し冪等性を保証。
  - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去する URL 正規化。
  - defusedxml を用いて XML インジェクション等を防止。
  - SSRF 対策:
    - fetch 前にホストのプライベートアドレスチェックを実施。
    - リダイレクト時にもスキームとプライベートアドレスを検証するカスタムリダイレクトハンドラを実装。
    - http/https 以外のスキームを明示的に拒否。
  - レスポンスサイズ上限（デフォルト 10MB）を設定し、Content-Length チェックと読み取り上限でメモリDoSや Gzip bomb を防止。
  - gzip 圧縮レスポンスの解凍対応（解凍後サイズ検査含む）。
  - RSS の pubDate を適切にパースして UTC naive datetime に変換。パース失敗時は警告ログを出して現在時刻で代替。
  - DB 保存はバルク INSERT（チャンクサイズ 1000）とトランザクション管理を行い、INSERT ... RETURNING で実際の挿入件数を返す:
    - save_raw_news: raw_news テーブルへの登録（ON CONFLICT DO NOTHING、挿入された id を返す）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの記事-銘柄紐付けを一括保存（重複除去・トランザクション）。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）を提供。
  - デフォルト RSS ソースに Yahoo ビジネスカテゴリを設定。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）と Execution 層のテーブル群を定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル整合性（PRIMARY KEY / FOREIGN KEY / CHECK 制約）を定義。
  - 実行時の頻出クエリに備えたインデックスを作成。
  - init_schema(db_path) でデータベースファイルの親ディレクトリ作成を行い全DDL/インデックスを適用する冪等な初期化処理を提供。
  - get_connection(db_path) で既存 DB へ接続するヘルパを提供。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL の設計に基づくヘルパを実装。
  - ETLResult データクラスを実装し、取得・保存件数、品質問題、エラー一覧を格納。品質問題は serializable な辞書に変換可能。
  - テーブル存在確認、指定カラムの最大日付取得ユーティリティを実装。
  - market_calendar を参照して非営業日を直近営業日に調整する _adjust_to_trading_day を実装。
  - raw_prices/raw_financials/market_calendar の最終取得日を返す get_last_* 関数を実装。
  - run_prices_etl を実装（差分取得、backfill_days による後出し修正吸収ロジック、J-Quants 呼び出しと保存）。（ETL の品質チェックや他ジョブとの統合は別モジュール quality と連携する設計）

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の注意点 / 設計上の決定
- .env 読み込みはプロジェクトルート探索に依存するため、配布後に期待通り動作させるにはプロジェクトルートが存在すること（.git または pyproject.toml）を想定しています。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自前で環境を注入してください。
- J-Quants API の retry/refresh ポリシーは一般的なケースを想定しており、特定ワークロードでのスロットリングやレート制御は運用に応じて調整してください。
- news_collector は外部ネットワークの取り扱いに慎重な実装（SSRF/サイズ制限/defusedxml）を行っていますが、RSS コンテンツの多様性により追加のパース例外が発生する可能性があります。
- ETL パイプラインは差分更新・バックフィルの基本ロジックを提供しています。品質チェック（quality モジュール）による判定結果に基づく運用判断は呼び出し元が行う設計です。

### セキュリティ
- defusedxml の利用、SSRF 対策（プライベートIPチェック、リダイレクト検査）、許可スキーム制限、レスポンスサイズ制限などを実装して外部入力からの攻撃面を低減しています。
- .env の読み込みは OS 環境変数を保護するため protected キーセットを用いて上書き制御を行います。

---

今後の予定（提案）
- ETL の完全なジョブ（財務・カレンダー・ニュースの統合 ETL）と品質チェックの自動化フローを拡充。
- strategy / execution / monitoring サブモジュールの実装（シグナル生成、注文実行、状態監視・アラート）。
- テストカバレッジの追加（ネットワーク部分のモック、DB 初期化を伴う統合テスト等）。