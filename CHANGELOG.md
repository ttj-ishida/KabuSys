# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

現時点でのリリース履歴（コードベース内容から推測）:

## [Unreleased]
- 今後の実装予定:
  - ETL パイプラインの追加ジョブ（財務データ・カレンダーの差分ETL 等）の完成
  - 品質チェックモジュール（quality）の統合とETLフローでの挙動制御
  - 単体テスト・統合テストの追加
  - CI/CD やパッケージングの整備

---

## [0.1.0] - 2026-03-17

Added
- プロジェクト初期リリース相当の機能を追加。
  - パッケージのエントリポイントを設定
    - src/kabusys/__init__.py にて version "0.1.0"、公開モジュールを定義。
  - 設定管理 (src/kabusys/config.py)
    - .env / .env.local または環境変数から設定値を読み込む自動ローダーを実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env の行パーサーは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須環境変数チェック (_require) と Settings クラス：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の取得プロパティ。
      - KABUSYS_ENV / LOG_LEVEL の検証（有効な値セットを検査）。
      - DB ファイルパス設定（DUCKDB_PATH, SQLITE_PATH）の取り扱い。
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - ベース機能:
      - API ベース URL、認証、ページネーション対応のデータ取得関数を実装:
        - fetch_daily_quotes（株価日足）
        - fetch_financial_statements（四半期財務）
        - fetch_market_calendar（JPX カレンダー）
    - 信頼性向上のための設計:
      - 固定間隔のレートリミッタ（120 req/min）を実装。
      - 再試行ロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）。
      - 401 時はトークンを自動リフレッシュして1回だけリトライ。
      - ページネーション用のトークンキャッシュを実装。
    - DuckDB への保存関数（冪等性を意識）:
      - save_daily_quotes, save_financial_statements, save_market_calendar：
        - ON CONFLICT DO UPDATE を用いた重複排除／上書き。
        - PK 欠損行はスキップしログ出力。
      - データ変換ヘルパー: _to_float, _to_int（堅牢な型変換、空値処理等）。
    - ロギングにより各処理の取得件数・保存件数を報告。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードからの記事収集と DuckDB への保存機能を実装。
    - セキュリティと堅牢性:
      - defusedxml を使った XML パース（XML Bomb 対策）。
      - SSRF を防ぐための検査:
        - URL スキーム検証（http/https のみ許可）。
        - ホストがプライベート/ループバック/リンクローカルでないか判定（DNS 解決＋IP 判定）。
        - リダイレクト時にも検証する _SSRFBlockRedirectHandler を実装。
      - レスポンス最大バイト数制限（10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）。
      - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - データ保存・紐付け:
      - save_raw_news: チャンク化した INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入 ID を返す（トランザクションでまとめる）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（重複排除、RETURNING で正確な挿入数取得）。
    - 銘柄コード抽出:
      - 正規表現により 4 桁数字候補を抽出し、known_codes に基づきフィルタ。
    - デフォルト RSS ソースを定義（例: Yahoo Finance の business RSS）。
  - DuckDB スキーマ定義 (src/kabusys/data/schema.py)
    - Raw / Processed / Feature / Execution の多層スキーマを定義。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等 Processed テーブル。
    - features, ai_scores の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等 Execution テーブル。
    - インデックス定義と依存を考慮したテーブル作成順を提供。
    - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス作成を実行するヘルパーを実装。
    - get_connection(db_path) で既存 DB への接続を取得可能。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
    - ETLResult データクラス（取得件数、保存件数、品質問題、エラー等を保持）。
    - テーブル存在チェック、最大日付取得ユーティリティを実装。
    - 市場カレンダーに基づく営業日補正ヘルパー。
    - 差分更新戦略（最終取得日からの backfill_days 再取得）を組み込んだ run_prices_etl を実装（差分取得→保存→ログ）。
    - 設計方針として品質チェックは検出しても ETL を継続（呼び出し元で判断）する形を採用。
  - モジュール公開:
    - src/kabusys/data/__init__.py, execution, strategy のパッケージ構造を用意。

Security
- RSS パースで defusedxml を利用し、XML 関連攻撃を軽減。
- RSS フェッチ時の SSRF 対策（スキーム検証、プライベートIP検出、リダイレクト検査）。
- .env ローダーは OS 環境変数を保護する protected 機構を採用。

Performance / Reliability
- API コールは固定間隔レートリミッタ（120 req/min）によりレート制御。
- 再試行・指数バックオフ・429 の Retry-After 対応により一時障害に耐性。
- DuckDB へのバルク INSERT はチャンク化してトランザクションでまとめ、ON CONFLICT / RETURNING を利用して冪等性と正確な挿入数取得を両立。

Fixed
- （初版）実装上の基本的なエラーハンドリングとログ出力を整備。

Known limitations / Notes
- run_prices_etl の戻り値部分や pipeline の一部処理が実装途上（提示コードの末尾で戻り値のタプルが途切れている等）、追加実装・テストが必要。
- quality モジュールは参照されているが実装詳細はこのコードベースには含まれていない（品質チェックの具体的ルールは別実装が必要）。
- デフォルト RSS ソースは一つ（yahoo_finance）に限定。外部ソース追加は可能。
- 単体テスト・統合テストは含まれていないため、実運用前にテストを追加することを推奨。
- 一部エラー時に ValueError を投げる設計（必須環境変数の欠如等）。運用時は必須環境変数の設定を確認すること。

Security
- 初版リリースのため、依存ライブラリの脆弱性チェック（defusedxml 等を含む）とセキュリティ監査を推奨。

---

タグ/リンク:
- 比較用: このファイルは Keep a Changelog の基本的なカテゴリ（Added, Changed, Fixed, Security）に従っています。将来的なリリースでは Unreleased→バージョンに移行し、詳細な変更差分（コミットや PR 番号）を付記してください。