CHANGELOG
=========

すべての変更は "Keep a Changelog" のフォーマットに従います。  
このプロジェクトはセマンティックバージョニングに従います。  

リンク: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-03-17
------------------

Added
- 初版リリース: KabuSys — 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージ情報
    - パッケージバージョンを 0.1.0 に設定。
    - パッケージ public API として data, strategy, execution, monitoring を公開。

  - 環境設定 / 設定管理 (kabusys.config)
    - .env と .env.local の自動読み込み機能を実装（OS 環境変数を優先、.env.local は上書き）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動ロードを実現。
    - 読み込みの無効化オプション KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサ実装: export 形式、クォート/エスケープ処理、インラインコメント対応。
    - Settings クラスでアプリ設定をプロパティ経由で提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル検証など）。
    - 必須環境変数未設定時に明示的なエラーを投げる _require() を実装。

  - J-Quants API クライアント (kabusys.data.jquants_client)
    - 日足（OHLCV）、財務データ、マーケットカレンダー取得関数を追加（ページネーション対応）。
    - 認証: リフレッシュトークンから id_token を取得する get_id_token を実装。
    - HTTP ユーティリティ:
      - 固定間隔の RateLimiter を実装し、120 req/min を順守するスロットリングを追加。
      - 再試行ロジック (指数バックオフ, 最大 3 回)。対象ステータス (408, 429, 5xx) に対応。
      - 401 受信時に自動で一度トークンをリフレッシュして再試行する機能を追加（無限再帰防止の allow_refresh フラグ）。
    - 保存関数（DuckDB）:
      - raw_prices / raw_financials / market_calendar への冪等保存（ON CONFLICT DO UPDATE）を実装。
      - fetched_at に UTC ISO タイムスタンプを記録し、Look-ahead Bias の追跡を可能に。
      - 型安全変換ユーティリティ (_to_float, _to_int) を導入。

  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィード取得および raw_news への保存機能を実装。
    - セキュリティ・堅牢性強化:
      - defusedxml を用いた XML パースで XML ボム等を防止。
      - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検査、プライベート/ループバック/リンクローカル IP の検出と拒否。
      - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を実装し、読み込み超過は安全にスキップ。
      - gzip 解凍時のサイズ再検査（Gzip bomb 対策）。
      - User-Agent と Accept-Encoding を設定してフェッチ。
    - 冪等性 / ID 生成:
      - 記事 ID を URL を正規化（トラッキングパラメータ削除、ソート、フラグメント除去）した上で SHA-256（先頭32文字）で生成し重複を排除。
      - save_raw_news はチャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING を使い、実際に挿入された ID を返す。
      - news_symbols への紐付け保存も INSERT ... RETURNING を使い、トランザクション管理を行う。
    - テキスト前処理（URL 除去、空白正規化）と RSS pubDate の堅牢なパース（タイムゾーン処理）を実装。
    - 銘柄コード抽出ロジック（4桁数字、known_codes フィルタ）を追加。

  - DuckDB スキーマ管理 (kabusys.data.schema)
    - Raw / Processed / Feature / Execution の多層スキーマを定義。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル、features / ai_scores の Feature テーブル、signals / signal_queue / orders / trades / positions / portfolio_performance 等の Execution テーブルを DDL として追加。
    - 必要なインデックスを作成するDDLを追加（頻出クエリの高速化目的）。
    - init_schema(db_path) によりディレクトリ作成 → 全テーブルとインデックスの冪等作成を行い、DuckDB 接続を返す。get_connection() で既存 DB に接続。

  - ETL パイプライン (kabusys.data.pipeline)
    - ETL の設計と一部実装（差分更新、バックフィル、calendar の先読み概念など）。
    - ETLResult データクラスにより ETL 実行の結果・品質問題・エラーを集約して返す仕組みを追加。
    - 市場カレンダーを参照して営業日に調整する _adjust_to_trading_day を実装。
    - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を提供。
    - run_prices_etl の基本ロジック（最終取得日からの差分算出、fetch_daily_quotes → save_daily_quotes の呼び出し）を追加。
    - 品質チェックフレームワーク（quality モジュール呼び出しを想定）との連携用に設計。

  - 空モジュールのプレースホルダ
    - strategy と execution パッケージに __init__.py を追加し将来の拡張に備える。

Security
- ニュース収集に関する SSRF 対策、defusedxml による XML セキュアパース、レスポンスサイズ制限を明示。
- URL 正規化時のトラッキングパラメータ除去で ID 一意性を安定化。

Other
- ロギングを各モジュールに追加（情報・警告の出力により運用時の診断が容易）。
- DuckDB を中心とした軽量な組み込みデータストアを採用し、ETL と保存処理の冪等性を優先。

Known issues / Notes
- pipeline.run_prices_etl は基本的なフローを実装していますが、品質チェック連携や一部戻り値・例外ハンドリングは更なる整備が想定されます（コードベース内に継続実装の余地あり）。
- strategy / execution モジュールはプレースホルダであり、発注ロジック・取引実行部分は今後実装予定。
- 単体テスト・統合テスト、ドキュメント（DataPlatform.md / DataSchema.md 参照）は別途整備が必要です。

Contributors
- 初版実装者（コードベースから推測）。

-- end of changelog --