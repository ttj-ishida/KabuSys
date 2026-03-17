CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルではパッケージ kabusys の初回リリース（v0.1.0）で実装された主な機能・設計上の注意点を日本語でまとめています。

[Unreleased]
------------

- なし（初回リリース v0.1.0 を参照してください）。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース。日本株自動売買システムの基礎モジュール群を実装。
  - kabusys.__init__ にてバージョン "0.1.0" を設定。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダを実装。読み込み優先順は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml から行い、パッケージ配布後も動作するよう設計。
  - .env 行のパースに対応：
    - コメント・空行を無視、export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメント扱いの判定ロジックなど。
  - auto load を無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途など）。
  - Settings クラスを公開（プロパティ経由で設定値取得）。必須値未設定時は ValueError を投げる _require を提供。
  - 環境値のバリデーション：
    - KABUSYS_ENV: development / paper_trading / live のみ許可。
    - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL のみ許可。
  - Slack / J-Quants / kabu API / DB パス等のプロパティを用意。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得機能を実装（fetch_* 系関数）。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先。
  - 認証: refresh token から id_token を取得する get_id_token、モジュールレベルの id_token キャッシュ、401 受信時の自動リフレッシュ（1回のみ）を実装。
  - ページネーション対応（pagination_key を使った列挙）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。すべて冪等（ON CONFLICT DO UPDATE）で保存。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias のトレースを容易にする設計。
  - 型変換ユーティリティ（_to_float, _to_int）を備え、入力の頑健な取り扱いを行う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を提供。
  - セキュリティ/堅牢性対策：
    - defusedxml を用いた XML パース（XML Bomb 等に対する保護）。
    - SSRF 対策: リダイレクト時にスキーム/ホストを検証するカスタム RedirectHandler、ホストのプライベートアドレス判定、http/https スキームのみ許可。
    - レスポンスの最大受信バイト数（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の上限チェック（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）による一意な記事ID生成（SHA-256 の先頭32文字）。
  - テキスト前処理（URL 削除、空白正規化）関数を提供。
  - RSS 取得関数 fetch_rss は XML パース失敗時に警告ログを出力して空リストでフォールバック。
  - DuckDB への保存:
    - save_raw_news: チャンク挿入、1 トランザクションでの処理、INSERT ... RETURNING で挿入された新規記事IDを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存。チャンク処理とトランザクションを実装。
  - 銘柄コード抽出ロジック: 4桁数字候補から known_codes に含まれるもののみを抽出（重複除去）。
  - run_news_collection: 複数ソースの収集ジョブを実装。各ソースは独立してエラーハンドリングし、失敗しても他ソースは継続。新規記事に対する銘柄紐付けをまとめて挿入。

- DuckDB スキーマ定義 / 初期化（src/kabusys/data/schema.py）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル DDL を実装。
  - 主要テーブルを網羅:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主キー・チェック制約・外部キーを明示。頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ自動作成・DDL 実行して接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（差分 ETL）のためのユーティリティ群と基本ジョブを実装。
  - 設計方針の反映:
    - 最終取得日を基に差分を算出し、backfill_days（デフォルト 3 日）で後出し修正を吸収。
    - 市場カレンダーは先読み（_CALENDAR_LOOKAHEAD_DAYS=90 日）。
    - 品質チェック（quality モジュール）との連携ポイントを用意（品質問題は収集を継続しつつ報告）。
  - ETLResult dataclass を導入（品質問題の要約・エラーフラグ・辞書化メソッドを含む）。
  - テーブル存在チェック、最大日付取得、営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - 個別ジョブの雛形（run_prices_etl 等）を実装（差分算出、fetch → save のフロー）。

Security
- RSS/XML 関連で defusedxml を採用し、SSRF（リダイレクト先検証・プライベートアドレス拒否）・レスポンスサイズ制限・gzip 解凍後の上限チェックなど複数の防御策を実装。
- .env 読み込みで既存 OS 環境変数の保護（protected set）や自動ロード無効フラグを提供。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / TODO
- pipeline モジュールは ETL の基本的なフローとヘルパーを実装していますが、quality モジュールや完全なスケジューリング / ジョブ実行ロジックは別モジュール（未表示）と連携する想定です。
- jquants_client の HTTP 呼び出しは urllib を直接使用しており、テストでは id_token 注入や _rate_limiter の制御、news_collector._urlopen のモック差し替えで振る舞いを置き換え可能です。
- 監査ログや運用上のメトリクス（API コール数、失敗率など）は今後の拡張ポイントです。

作者
- 実装に基づく推定情報により CHANGELOG を作成しました。実際のコミット履歴が存在する場合はそちらを優先して差分を更新してください。