CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。重要な変更点（機能追加、修正、セキュリティ関連など）を日本語で記載します。

Unreleased
----------

（現在のコードベースでは未リリースの変更はありません）

[0.1.0] - 2026-03-17
-------------------

初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア基盤を実装。

Added
- パッケージ構成
  - kabusys パッケージの骨格を実装（src/kabusys/__init__.py）。バージョンは 0.1.0、公開サブパッケージとして data, strategy, execution, monitoring を宣言。

- 環境変数/設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して判定（CWD に依存しない）
  - .env パーサ実装（コメント、export 句、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱いなど）
  - Settings クラスを提供し、必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）と入力検証（KABUSYS_ENV, LOG_LEVEL）、および便利プロパティ（is_live/is_paper/is_dev, duckdb/sqlite の既定パス）を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API レート制限制御（固定間隔スロットリング）を実装（120 req/min を遵守）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回、対象: 408/429/5xx）。
    - 429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にリフレッシュトークンから自動で id_token を更新して 1 回だけ再試行する仕組みを導入（無限再帰を回避）。
  - ページネーション対応（pagination_key）の取得ロジック。
  - データ取得関数を提供:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性を担保）:
    - save_daily_quotes（raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - データ品質を考慮したユーティリティ（_to_float, _to_int）、および取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news テーブルに保存する一連処理を実装。
  - セキュリティ・堅牢性:
    - defusedxml を使用して XML Bomb 等を防止。
    - HTTP リダイレクトに対して SSRF 対策を行うカスタム RedirectHandler を導入（スキーム検証、プライベートIP/ループバック/リンクローカルの排除）。
    - 最終 URL の再検証、ホストのプライベート判定（DNS 解決した A/AAAA を検査）、および初期 URL の事前チェック。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を設け、Gzip 解凍後のサイズもチェック（Gzip bomb 対策）。
    - URL スキームの検証（http/https のみ許可）。
  - データ処理・永続化の方針:
    - 記事ID は URL 正規化（utm_* 等のトラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）した上で SHA-256 の先頭32文字で生成 → 冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）。
    - INSERT ... RETURNING を使用して実際に新規挿入された記事のみを返す（チャンク単位でのバルク挿入、トランザクションでまとめる）。
    - news_symbols（記事と銘柄コードの紐付け）は重複除去→チャンク挿入→INSERT ... RETURNING を用いて正確な挿入数を返す。
  - 銘柄コード抽出:
    - 4桁数字のパターンから既知銘柄セットと照合して抽出（重複除去）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - カラム型／制約（CHECK, PRIMARY KEY, FOREIGN KEY）を詳細に定義。
  - 頻出クエリ向けインデックス定義を提供（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ自動作成、テーブル作成（冪等）およびインデックス作成を行い DuckDB 接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（incremental）方式の ETL 実装方針を実装開始:
    - DB の最終取得日を参照して差分のみを取得
    - backfill_days による過去再取得（デフォルト 3 日）で API の後出し修正に耐性
    - 市場カレンダーは将来分を先読みする仕組み（_CALENDAR_LOOKAHEAD_DAYS）
  - ETL 実行結果を表す ETLResult データクラスを追加（品質チェック結果やエラー一覧を保持、辞書化可能）。
  - テーブル存在チェック、最大日付取得、営業日調整などのユーティリティ関数を提供。
  - run_prices_etl の差分ロジックを実装（取得 → 保存の流れ）。（注: pipeline モジュールは今後拡張予定）

Changed
- （初版のため変更履歴なし）

Fixed
- （初版のため修正履歴なし）

Security
- 複数モジュールでセキュリティ対策を実装:
  - RSS の XML パースに defusedxml を使用（XML インジェクション/DoS 対策）
  - SSRF 対策（リダイレクト時のスキーム/ホスト検査、プライベートIP拒否、DNS 検証）
  - レスポンスサイズ制限（メモリ DoS / Gzip bomb 対策）
  - .env 読み込みはファイルアクセス失敗時に警告を出すが安全にフォールバック
  - DB 書き込みはトランザクション単位で行い、失敗時はロールバックして例外を再送出

Notes / 今後の予定
- strategy, execution, monitoring サブパッケージはプレースホルダとして存在。戦略ロジック、実行エンジン、監視・通知機能（Slack 連携など）は今後追加予定。
- ETL の品質チェック（quality モジュール）とその統合は pipeline 側で継続実装予定。
- 単体テスト・統合テスト、CI 設定、パッケージ配布（wheel / PyPI）などの整備を進める予定。

署名
- KabuSys 開発チーム

---