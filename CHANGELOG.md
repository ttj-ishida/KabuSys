CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」規約に従って記載しています。
このファイルは、リポジトリのコードから推測できる実装内容・変更点を基に作成した推定の変更履歴です（実際のコミット履歴ではありません）。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-18
--------------------

追加 (Added)
- 初回公開: KabuSys 0.1.0 — 日本株自動売買システムの基盤機能を実装。
  - パッケージ初期化
    - src/kabusys/__init__.py にバージョン (0.1.0) と公開モジュール一覧を定義。
  - 環境変数 / 設定管理
    - src/kabusys/config.py
      - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
      - export 形式やクォート、インラインコメントなどを考慮した .env パーサ実装。
      - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
      - 必須環境変数取得ヘルパ _require と Settings クラスを実装（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル検証を含む）。
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得機能を実装。
      - レート制御: 固定間隔スロットリング (_RateLimiter) により 120 req/min を順守。
      - 再試行ロジック: 指数バックオフ、最大3回、408/429/5xx をリトライ対象。
      - 401 時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ機構。
      - ページネーション対応の fetch_* 関数群（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT を用いた更新）。
      - 値変換ユーティリティ (_to_float, _to_int) を実装しデータ整合性を強化。
  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィードからのニュース収集パイプラインを実装（取得 → 前処理 → DB保存 → 銘柄紐付け）。
      - セキュリティ対策:
        - defusedxml を用いた XML パース（XML Bomb 対策）。
        - リダイレクト検査・SSRF 対応（プライベートIP/ループバック/リンクローカルの検出と拒否）。
        - URL スキーム検証（http/https のみ許可）。
        - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip-bomb 対策）。
      - URL 正規化・トラッキングパラメータ除去、記事ID を SHA-256（先頭32文字）で生成して冪等性を確保。
      - raw_news テーブルへのチャンク挿入とトランザクション管理（INSERT ... RETURNING を利用して実際に挿入された ID を返す）。
      - 銘柄コード抽出ロジック（4桁数字パターン + known_codes フィルタ）。
      - run_news_collection: 複数ソースを独立して処理し、失敗ソースがあっても他を継続。
  - DuckDB スキーマ管理
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の多層スキーマを定義。
      - raw_prices, raw_financials, raw_news, raw_executions などの Raw 層テーブル。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
      - features, ai_scores 等の Feature 層。
      - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
      - 適切な CHECK 制約・PRIMARY KEY・外部キーを含むDDLを用意。
      - 頻出クエリ用のインデックス定義を用意。
      - init_schema(db_path) でディレクトリ作成、テーブル作成、インデックス作成まで行い、DuckDB 接続を返す。
      - get_connection(db_path) により既存DBへ接続可能（スキーマ初期化は行わない）。
  - ETL パイプライン基盤
    - src/kabusys/data/pipeline.py
      - 差分取得とバックフィルを考慮した ETL ワークフロー設計。
      - ETLResult データクラスによる結果集約（品質問題・エラーの収集）。
      - テーブル存在チェック、最終取得日取得ヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
      - 市場カレンダーを考慮して非営業日を直近の営業日に調整するヘルパ。
      - run_prices_etl の骨子（差分算出 → jq.fetch_daily_quotes → jq.save_daily_quotes）を実装。
  - その他
    - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py を配置（モジュール構造の整備）。
    - ロギング（各モジュールで logger を利用）を考慮した実装。

変更 (Changed)
- なし（初回リリースのため変更履歴はなし）。

修正 (Fixed)
- なし（初回リリースのため修正履歴はなし）。

セキュリティ (Security)
- RSS / HTTP 周りで複数のセキュリティ対策を追加:
  - defusedxml を用いた安全な XML パース。
  - リダイレクト時のスキーム・ホスト検査とプライベートアドレス拒否（SSRF 防止）。
  - レスポンスサイズ制限と gzip 解凍後の再チェック（メモリ DoS / Gzip-bomb 対策）。
  - URL スキームの厳格チェック（http/https のみ）。
- J-Quants API クライアントでの例外 / 再試行ポリシーにより一時障害からの復旧性を向上。

既知の問題・今後の TODO
- pipeline.run_prices_etl の戻り値が現状では (len(records), ) として不完全に見える（コメントや実装の途中と思われる）。呼び出し側が (fetched, saved) の 2 値を期待する設計のため、保存結果(saved) を返すよう修正が必要。
- execution/strategy パッケージは __init__ のみで実装が空のため、発注実行ロジックや戦略本体は未実装。
- テスト群（ユニット/統合テスト）がコード内に存在しないため、CI 用テストケースの追加が必要。
- DuckDB スキーマは多くの制約を含むが、実運用での挙動確認（大規模データ挿入やパフォーマンス）は未評価。
- ニュース収集の既知銘柄リスト（known_codes）の取得方法は外部から注入する設計だが、既定の取得手段は未実装。

注記
- この CHANGELOG は、提示されたソースコードから推測して記載した「初期リリースの機能一覧および設計上の注記」です。実際のコミット/リリースノートに基づく履歴ではないため、必要に応じて実際の履歴や運用ポリシーに合わせて修正してください。