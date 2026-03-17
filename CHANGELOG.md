CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（現状、リポジトリ提供の内容は初回リリース相当のため、未リリース変更はありません。）

[0.1.0] - 2026-03-17
-------------------

初回リリース (コードベースから推測して記載)。

Added
- パッケージ基盤
  - パッケージ定義（kabusys）を追加。__version__ = 0.1.0、公開モジュール（data, strategy, execution, monitoring）を __all__ に設定。
  - strategy/ と execution/ パッケージのスケルトンを配置（将来の戦略・実行ロジックのためのエントリポイントを確保）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索し、配布後でも cwd に依存しない動作を実現。
  - 自動 .env 読み込み: OS 環境変数 > .env.local > .env の優先度で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理
    - クォート無しのインラインコメント（#）処理
  - 必須環境変数取得メソッド _require を実装（未設定時は ValueError）。
  - Settings に J-Quants / kabuステーション / Slack / データベースパス等のプロパティを追加。KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許可値の検証）を行うユーティリティを提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能:
    - 株価日足（OHLCV）取得 fetch_daily_quotes
    - 財務データ（四半期 BS/PL）取得 fetch_financial_statements
    - JPX マーケットカレンダー取得 fetch_market_calendar
  - 信頼性・スケーリング設計:
    - レート制限の保護: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter を実装。
    - リトライロジック: 指数バックオフ（最大 3 回）、408/429/5xx を対象にリトライ。429 の場合は Retry-After を優先。
    - 認証/トークン管理: get_id_token で refresh_token から id_token を取得。モジュールレベルで id_token をキャッシュしページネーション間で共有。401 を受けた場合はトークンを1回自動リフレッシュして再試行。
    - JSON デコード失敗時の明示的エラー。タイムアウトやネットワーク例外へのロギングと再試行。
  - DuckDB 保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。いずれも冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - 取得時刻 fetched_at を UTC で記録（Look-ahead Bias を抑えるトレース可能設計）。
    - 型変換ユーティリティ _to_float / _to_int を実装（空値や変換失敗時の挙動を明確化、"1.0" などの float 文字列からの安全な int 変換など）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存するフローを実装。
  - 設計／セキュリティ対策:
    - XML パースに defusedxml を利用し XML Bomb 等の攻撃対策。
    - SSRF 対策:
      - 初回ホスト検査でプライベート IP の排除 (_is_private_host)。
      - リダイレクト時にもスキーム／ホスト検査を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）を使用。
      - http/https スキーム以外の URL を拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査による Gzip-bomb 対策。
    - 記事 ID は URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリのソート等）後の SHA-256 ハッシュ先頭32文字で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news はチャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事 ID のリストを返す（トランザクションでまとめる）。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けを一括挿入（ON CONFLICT で重複を無視）する。INSERT ... RETURNING を使用して挿入実績を正確に取得。
  - 銘柄抽出:
    - extract_stock_codes: 正規表現で 4 桁数字を抽出し、known_codes に含まれるもののみを返す（重複排除）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform 構成に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約・PRIMARY KEY / FOREIGN KEY を定義。
  - 頻出クエリ向けのインデックスを用意（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) を実装し、親ディレクトリの自動作成・DDL 実行・インデックス作成を行う（冪等）。get_connection() で既存 DB へ接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を導入し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を集約可能に。
  - 差分更新ユーティリティ:
    - テーブルの最終取得日取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 営業日補正ヘルパー _adjust_to_trading_day（market_calendar に基づき非営業日を直近の営業日に調整）。
    - run_prices_etl 実装（差分更新ロジック、backfill_days による過去再取得、J-Quants からの取得→保存のフロー）。HTTP トークン注入に対応（id_token 引数）。
  - 設計方針として、品質チェック（quality モジュール）を呼び出し元で扱えるようにし、Fail-Fast とせず全件収集を優先する方針を採用。

Security
- ニュース収集に関する複数のセキュリティ対策を実装（defusedxml、SSRF 検査、レスポンスサイズ制限、gzip 解凍後検査）。
- .env ローダーは OS 環境変数を保護するため protected セットを導入し、.env.local による上書きも OS 環境変数を上書きしないよう配慮。

Performance
- J-Quants クライアントに固定間隔のレートリミッタを導入（120 req/min）。
- news_collector の DB 書き込みはチャンク化してバルク INSERT を行い、トランザクションをまとめてオーバーヘッドを削減。
- id_token はモジュールレベルでキャッシュしてページネーション間の効率を向上。

Notes / Limitations
- strategy と execution パッケージはスケルトン（実装なし）で残されており、実際の売買ロジックや注文送信は未実装。
- pipeline.run_prices_etl の後続ジョブ（財務データ、カレンダー、品質チェック連携）はパイプライン設計に従って拡張が必要（コードベースに示されている設計方針を参照）。
- DuckDB を前提としているため、実行環境に duckdb が必要。

Acknowledgements / Design
- 各モジュールに設計意図（Look-ahead Bias 防止、冪等性、セキュリティ対策、再現可能性のための fetched_at 記録 等）が明記されており、データプラットフォーム運用を念頭に置いた実装になっています。

今後の予定（推測）
- strategy / execution の実装（シグナル生成・注文送信）
- 品質チェックモジュール quality の統合と自動アラート
- モニタリング（monitoring）と Slack 通知の実装

-----