Changelog
=========
この CHANGELOG は Keep a Changelog の形式に準拠しています。  
すべての重要な変更点を日本語で記載しています。

未リリース
---------
（なし）

[0.1.0] - 2026-03-17
-------------------
初回リリース — KabuSys: 日本株自動売買システムの基盤モジュール群を実装。

Added
- パッケージ骨組み
  - src/kabusys/__init__.py
    - パッケージ名と __version__ を定義（0.1.0）。
    - 公開サブパッケージ: data, strategy, execution, monitoring を設定。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env と .env.local の読み込み順序、OS 環境変数保護の仕組みを実装。
    - パースロジック: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理をサポート。
    - Settings クラスを公開（必須変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）、LOG_LEVEL の検証。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出しユーティリティ（_request）を実装。
      - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
      - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象に設定。
      - 401 を受け取った場合はリフレッシュトークンから id_token を自動更新して 1 回リトライ。
      - JSON デコード失敗時の詳細エラーメッセージ。
    - 認証ヘルパー get_id_token（リフレッシュトークン→idToken）。
    - データ取得関数:
      - fetch_daily_quotes（ページネーション対応で株価日足を取得）
      - fetch_financial_statements（四半期 BS/PL をページネーション取得）
      - fetch_market_calendar（JPX マーケットカレンダー取得）
    - DuckDB 保存ユーティリティ（冪等）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - INSERT ... ON CONFLICT DO UPDATE を使用し冪等性を保証。
    - 型変換ユーティリティ: _to_float, _to_int（誤変換防止ロジック含む）。
    - fetched_at に UTC タイムスタンプを記録し、Look-ahead バイアス対策を考慮。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集・前処理し DuckDB に保存する一連の機能を実装。
    - セキュリティと堅牢性:
      - defusedxml を用いた XML パース（XML Bomb 等を緩和）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベート IP 判定、リダイレクト先検査（カスタム RedirectHandler）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 展開後のサイズ検査（Gzip bomb 対策）。
      - 許可されないスキームやプライベートアドレスへのアクセスは拒否。
    - 正規化・識別:
      - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
      - 記事ID は正規化 URL の SHA-256 の先頭 32 文字を利用して冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id（チャンク分割 & トランザクション）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク保存（RETURNING ベースで実際の挿入数を返す）。
    - 銘柄抽出:
      - extract_stock_codes: テキスト中の 4 桁数字を抽出し known_codes に存在するもののみ返す。
    - 統合ジョブ:
      - run_news_collection: 複数 RSS ソースからの収集 → raw_news 保存 → 新規記事に対する銘柄紐付け（known_codes がある場合）。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の多層構造でテーブル定義を実装。
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 制約（CHECK, PRIMARY KEY, FOREIGN KEY）やインデックスを設計。典型的なクエリパターン（code×date、status 検索）に対するインデックスを作成。
    - init_schema(db_path) でディレクトリ作成（必要に応じ）と全 DDL の冪等実行を実装。get_connection で既存 DB へ接続。

- ETL / パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass（ETL 実行結果の構造化・品質検査結果保持）。
    - 差分更新ロジックの補助（最終取得日取得、営業日に調整するヘルパー）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - run_prices_etl の基礎（差分更新、バックフィル、jquants_client を使った取得→保存のフロー）を実装。バックフィル日数既定値: 3 日。
    - 各処理は id_token の注入が可能でテスト容易性を考慮。
    - 市場カレンダー先読みデフォルト値や J-Quants の最小データ日（2017-01-01）などの定数定義。

- その他
  - デフォルト DB パス: DuckDB: data/kabusys.duckdb、SQLite（監視用）: data/monitoring.db（config で Path として公開）。
  - デフォルト RSS ソースに Yahoo Finance（business カテゴリ）を登録。

Security
- RSS パーサーに defusedxml を採用し XML 関連の脆弱性を緩和。
- ニュース収集における SSRF 対策:
  - URL スキーム制限（http/https のみ）。
  - プライベート IP / ループバック / リンクローカル / マルチキャストのアクセス拒否（DNS 解決済みアドレスも検査）。
  - リダイレクト時の事前検査（カスタム RedirectHandler）。
- ネットワーク受信サイズ上限（10MB）および gzip 解凍後のサイズチェックを導入（メモリ DoS / Gzip bomb の軽減）。
- config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時の安全策）。

Notes / Known limitations / TODO
- strategy/ および execution/ パッケージは __init__.py のみで実装は最小（将来的に戦略・発注ロジックを追加予定）。
- quality モジュール参照（pipeline で使用）や監視（monitoring）周りの実装は本リリースでの依存を想定しているが、一部は外部実装を必要とする（実装状況に依存）。
- run_prices_etl など ETL の個別処理は基礎ロジックを実装済み。実運用向けの追加チェック（例: データ不整合の自動修正、より細かいロギングなど）は今後拡張予定。
- 現在のバージョンは初期実装のため、本番稼働前に環境変数設定（.env）、DuckDB スキーマ初期化、J-Quants / kabu API の認証情報、Slack 設定などを適切に用意してください。

ライセンス、貢献方法
- 本リポジトリのライセンス・貢献フローはリポジトリルートのドキュメント（LICENSE / CONTRIBUTING.md 等）を参照してください。

もし CHANGELOG に追加したい詳細（例: 日付の修正、より細かい変更単位、未記載のファイルなど）があれば教えてください。