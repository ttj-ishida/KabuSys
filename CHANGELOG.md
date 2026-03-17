CHANGELOG
=========

すべての重要な変更をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------

- 次回リリースでの変更点をここに記載します。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン番号: 0.1.0。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パースの強化:
    - export 形式対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理。
    - 無効行スキップ。
  - 環境変数取得ヘルパー _require を実装し、必須項目の未設定時に明示的なエラーを出す。
  - Settings クラスを追加し、J-Quants/ kabuステーション / Slack / DB パス / 環境（development/paper_trading/live） / ログレベルの取得と検証を提供。
  - パス類は Path 型で返却（expanduser を適用）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 経由で以下データを取得・保存する機能を実装:
    - 株価日足（fetch_daily_quotes / save_daily_quotes）
    - 財務データ（fetch_financial_statements / save_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - 設計上の要点:
    - 固定間隔のレート制御（120 req/min）を実装する RateLimiter（モジュール内 _RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408, 429, 5xx。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を防ぐ allow_refresh オプション）。
    - ページネーション対応（pagination_key の繰り返し取得）。
    - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）を利用。
    - データ取得日時（fetched_at）を UTC タイムスタンプで記録して Look-ahead Bias を防止。
  - 型変換ユーティリティ（_to_float / _to_int）を用意し、空値や形式不正を安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news / news_symbols へ保存する機能を実装。
  - 主な実装ポイント:
    - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）およびフラグメントを除去。クエリはキー順ソート。
    - defusedxml を用いた XML パースで XML Bomb を軽減。
    - SSRF 対策:
      - 初回 URL ホストのプライベートアドレスチェック（_is_private_host）。
      - リダイレクトごとにスキームとホストを検査するカスタムハンドラ _SSRFBlockRedirectHandler。
      - http/https 以外のスキーム拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェックと gzip 解凍後のサイズ検証（Gzip bomb への対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出（4桁数字）と既知銘柄フィルタリング。
    - DB への保存はチャンク化とトランザクションで行い、INSERT ... RETURNING を利用して実際の挿入数を正確に取得。
    - bulk の銘柄紐付け保存を提供し、重複排除とチャンク INSERT を行う。

- スキーマ管理（src/kabusys/data/schema.py）
  - DuckDB 用スキーマ定義と初期化関数 init_schema を実装。
  - 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックスを作成（頻出クエリに備えたインデックス群）。
  - init_schema は必要に応じて親ディレクトリを作成し、DDL を冪等に実行する。
  - get_connection を提供（初期化済み DB への接続取得）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL のためのユーティリティ群とデータクラスを追加:
    - ETLResult: 実行結果の構造化（取得件数・保存件数・品質問題・エラー等を含む）。
    - 差分更新ヘルパー: テーブル最終取得日の取得（get_last_price_date 等）。
    - 市場カレンダーを考慮した営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl を実装: 差分算出（最終取得日に基づくバックフィル）、J-Quants からの取得と保存を行う。id_token の注入によりテスト容易性を確保。
  - 設計上の方針: デフォルトのバックフィル日数は 3 日、品質チェックモジュール（quality）との連携ポイントを用意。

Security
- 環境変数読み込みは OS 環境変数を優先し、.env.local による上書き機能は OS 環境変数を保護する仕組み（protected set）を導入。
- ニュース収集での SSRF 対策、defusedxml の採用、レスポンスサイズ制限などセキュリティ対策を多数実装。

Performance
- J-Quants API 呼び出しのレート制御（固定間隔）とリトライで API 制限に配慮。
- news_collector の DB 挿入はチャンク化と単一トランザクションでオーバーヘッドを削減。
- DuckDB 側にインデックスを作成し、銘柄×日付の検索やステータス検索を高速化。

Notes / Implementation details
- get_id_token は settings.jquants_refresh_token を既定値として使用する。refresh_token がない場合は ValueError を発生させる。
- モジュールレベルの ID トークンキャッシュを導入し、ページネーション間でトークンを共有して効率化。
- RSS フィード取得用の _urlopen はテストでモック差し替え可能（テスト容易性を考慮）。
- 日時は内部的に UTC を基準に扱い、fetched_at は ISO 8601 Z 表記（一貫性確保）で保存。

Known issues / TODO
- quality モジュールとの詳細な連携（品質チェックルールの実装と扱い方）は今後の拡張対象。
- pipeline.run_prices_etl の周辺で、処理完了後の監査ログや通知の統合は未実装（将来のリリースで追加予定）。
- 今回のスナップショットでは一部インターフェース（例: execution / strategy パッケージ内の実装）が空のまま（プレースホルダ）。実際の発注ロジック・ストラテジ実装は今後実装予定。

参考
- 環境変数自動ロードをオフにするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。