# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティックバージョニングを使用しています。

## [Unreleased]
- （現状）strategy/execution パッケージはプレースホルダ（空の __init__.py）として用意されています。実装は未着手のため、将来のリリースで機能追加予定です。

---

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム (KabuSys) のコアモジュール群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開（strategy と execution は現時点では空のパッケージ）。
  - パッケージ全体の説明ドキュメンテーション文字列を追加。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機構を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ の親階層から `.git` または `pyproject.toml` を探索して実行（CWDに依存しない）。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサを実装（コメント行 / export プレフィックス / 引用符とエスケープ処理 / インラインコメントの扱い等に対応）。
  - 環境変数取得のラッパー `Settings` を実装。以下のプロパティを提供:
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）
    - 必須値取得時に未設定なら ValueError を送出する `_require` を導入（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。
  - 有効な環境値の検証:
    - KABUSYS_ENV: {development, paper_trading, live}
    - LOG_LEVEL: {DEBUG, INFO, WARNING, ERROR, CRITICAL}
  - DB パス（DuckDB / SQLite）はデフォルトを設定し Path 型で返す。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベース実装（HTTP リクエスト、認証、ページネーション、保存ロジック）を追加。
  - 設計上の特徴:
    - レート制限遵守（120 req/min）のため固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。再試行対象は 408/429 と 5xx、ネットワークエラーを再試行。
    - 401 Unauthorized を受け取った場合はトークンを自動リフレッシュして最大 1 回リトライ（無限再帰回避のため allow_refresh フラグを使用）。
    - ページネーション対応の fetch 関数群:
      - fetch_daily_quotes (日足 OHLCV)
      - fetch_financial_statements (四半期 BS/PL)
      - fetch_market_calendar (JPX カレンダー)
    - DB 保存は冪等性を担保（DuckDB への INSERT ... ON CONFLICT DO UPDATE を使用）。
    - 保存処理で fetched_at（UTC ISO8601、Z表記）を付与して「いつそのデータを知り得たか」をトレース可能に。
  - ユーティリティ:
    - 型安全な数値変換ヘルパー `_to_float`, `_to_int`（不正値は None を返す）。
    - get_id_token(refresh_token=None) でリフレッシュトークンから idToken を取得する POST 実装。
  - ロギングを使用して取得件数やリトライ状況を通知。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集して raw_news テーブルに保存する一連の機能を実装。
  - 主な特徴・設計:
    - デフォルト RSS ソース (Yahoo Finance のビジネスカテゴリ) を定義。
    - XML パースに defusedxml を利用し XML Bomb 等の攻撃を防御。
    - SSRF 対策:
      - fetch 前にホストがプライベート/ループバック/リンクローカルでないことを検証。
      - リダイレクト時にスキームとリダイレクト先がプライベートアドレスかを検査するカスタム redirect ハンドラを利用。
      - 許可スキームは http / https のみ。
    - レスポンスサイズ制限:
      - 最大受信サイズを 10MB に制限し、gzip 解凍後も確認（Gzip bomb 対策）。
    - URL 正規化と記事 ID 生成:
      - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去し、スキーム/ホスト小文字化、クエリソート、フラグメント削除を実施。
      - 正規化後の URL の SHA-256 ハッシュ先頭32文字を記事 ID として利用（冪等性担保）。
    - テキスト前処理（URL除去・空白正規化）。
    - DB 保存はトランザクションでチャンク INSERT、INSERT ... RETURNING を使って実際に挿入された ID/件数を正確に取得。
    - 銘柄コード抽出機能（4桁数字パターン、既知コード集合でフィルタ）。
    - run_news_collection: 複数ソースを独立に処理し、1ソース失敗でも他ソースを継続。新規挿入記事に対して銘柄紐付けをまとめて一括挿入。
  - エラーハンドリングとログ出力を充実。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform 設計に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK など）を設定し、整合性を担保。
  - 頻出クエリ向けのインデックスを追加。
  - init_schema(db_path) を実装:
    - ファイル DB の親ディレクトリを自動作成
    - 全テーブルとインデックスを冪等的に作成
    - ":memory:" によるインメモリ DB のサポート
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新ベースの ETL をサポートするヘルパ関数とジョブを実装開始。
  - 設計方針:
    - 差分更新のデフォルト単位は営業日1日分。DB の最終取得日から未取得範囲を自動算出。
    - backfill_days により最終取得日の数日前から再取得して後出し修正を吸収（デフォルト 3 日）。
    - 市場カレンダーの先読み日数: 90 日。
    - 品質チェックは外部モジュール (kabusys.data.quality) を参照し、品質問題が検出されても ETL を継続（呼び出し元でアクション判断）。
  - ETLResult データクラスを追加:
    - ETL 実行結果を構造化して保持（target_date, fetched/saved counts, quality_issues, errors 等）。
    - has_errors / has_quality_errors 等のユーティリティを提供。
    - to_dict() で品質問題をシリアライズ可能。
  - テーブル存在チェックや最大日付検出のユーティリティを実装（_table_exists, _get_max_date）。
  - 市場日調整ヘルパー (_adjust_to_trading_day) を実装（非営業日の場合は直近の営業日に調整、カレンダー未取得時は target_date をそのまま返す）。
  - 差分更新ジョブの一部実装:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
    - run_prices_etl の骨組みを実装（date_from の算出、fetch -> save を実行）。（注: run_prices_etl の戻り値の組が途中で切れているように見える箇所あり。詳細はソース参照）

### セキュリティ (Security)
- XML 関連の脆弱性対策:
  - defusedxml を使用して XML パースを行い、XML Bomb 等の攻撃を防止。
- ネットワーク / SSRF 対策:
  - RSS フェッチ前にホストがプライベート/ループバック/リンクローカルでないことを検査。
  - リダイレクト先も検証するカスタム HTTPRedirectHandler を導入。
  - 許可スキームは http / https のみ。
- 大量データや圧縮爆弾対策:
  - レスポンスの最大読み込みサイズを 10MB に制限し、gzip 解凍後も上限チェック。

### ドキュメント / ログ (Documentation / Logging)
- 各モジュールに設計方針や処理フロー、注意点を詳細にドキュメント化（モジュールトップの docstring）。
- 重要な処理（API 呼び出し、リトライ、DB 保存、スキップ件数など）で logger を通じて情報・警告・例外を出力。

### 既知の制限 / TODO
- strategy/execution モジュールは現時点では実装がないため、トレーディングロジック・発注処理は未実装。
- pipeline.run_prices_etl の戻り値や一部の実装はソースの最後で切れている（実装継続/整合性確認が必要）。
- quality モジュール参照はあるが、quality モジュール自体の詳細実装はここに含まれていない（別ファイルで実装想定）。
- DB スキーマは DuckDB に最適化されているが、実運用でのパフォーマンスチューニング（VACUUM・パーティショニング等）は未検討。

---

以上がコードベースから推測される初回リリースの CHANGELOG です。必要であれば項目ごとにさらに詳細（関数のシグネチャ、例外の挙動、ログメッセージの例など）を追記できます。どのレベルの詳細を希望しますか？