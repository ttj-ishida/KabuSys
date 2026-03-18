CHANGELOG
=========

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」準拠です。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージの初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git / pyproject.toml で検出）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パーサ（コメント、export プレフィックス、クォートとエスケープ対応）
  - 環境変数保護（既存 OS 環境変数を上書きしない保護セット）
  - 必須環境変数チェック (_require)
  - settings オブジェクト（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル判定 等）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API レート制御: 固定間隔スロットリング（120 req/min を想定する RateLimiter）
  - 汎用 HTTP リクエストヘルパー (_request)
    - JSON デコードエラーハンドリング
    - 再試行（指数バックオフ、最大 3 回）と 408/429/5xx への対応
    - 401 を受けた場合の ID トークン自動リフレッシュ（1 回のみ）
    - ページネーション対応（pagination_key）
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
  - 認証ヘルパー get_id_token（リフレッシュトークンから idToken を取得）
  - データ取得関数
    - fetch_daily_quotes（株価日足 OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE で保存
  - データ整形ユーティリティ: 安全な数値変換 _to_float / _to_int
  - Look-ahead bias 対策として fetched_at を UTC で記録する設計

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と記事パース（defusedxml を使用）
  - 安全性向上のための複数対策
    - URL スキーム検証（http/https のみ）
    - SSRF 対策: ホストのプライベートアドレス判定、リダイレクト先の検証（HTTPRedirectHandler 拡張）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）、gzip 解凍後も検査（Gzip bomb 対策）
    - XML パース失敗はログに残してスキップ
  - URL 正規化:
    - スキーム/ホスト小文字化、フラグメント削除、トラッキングパラメータ（utm_ 等）除去、クエリキーでソート
  - 記事 ID: 正規化 URL の SHA-256（先頭32文字）を採用して冪等性を確保
  - テキスト前処理: URL 除去、空白正規化
  - DB 保存機能（DuckDB）
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を利用、チャンク挿入、1 トランザクションで実行
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存、ON CONFLICT で重複を排除、RETURNING による実挿入数取得
  - 銘柄コード抽出: 4 桁数字パターン（例: "7203"）を known_codes と照合して抽出
  - デフォルト RSS ソース（yahoo_finance）を提供
  - run_news_collection: 複数ソースを独立して取得、部分失敗を許容しつつ new_ids を集約して銘柄紐付けを行う

- データスキーマ (kabusys.data.schema)
  - DuckDB 用 DDL を定義（Raw / Processed / Feature / Execution 層）
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - チェック制約や PRIMARY KEY を指定してデータ整合性を担保
  - 複数インデックス定義（頻出クエリ向け）
  - init_schema(db_path): ディレクトリ自動作成、DDL を冪等に実行して接続を返す
  - get_connection(db_path): 既存 DB への接続を返す（初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラス（取得数、保存数、品質問題、エラーの集約）
  - 差分更新用ユーティリティ:
    - テーブル存在チェック、テーブル最終日取得ヘルパー（get_last_price_date 等）
    - 市場カレンダーに基づく取引日の調整ヘルパー (_adjust_to_trading_day)
  - run_prices_etl: 差分更新のロジック（最終取得日 - backfill_days から再取得する既定挙動）、jquants_client の fetch/save を利用する設計
  - 品質チェック（quality モジュール）との連携を想定（重大度を集計して ETLResult に含める）

Performance / Reliability
- レート制御、再試行、トークンキャッシュにより API 呼び出しの安定化を図る
- DB 操作はチャンク・トランザクションでまとめ、INSERT ... RETURNING を使って正確な挿入結果を取得
- スキーマにチェック制約・インデックスを定義してデータ整合性と検索性能を改善

Security
- RSS 処理における XML 害対策に defusedxml を使用
- SSRF 対策: URL スキーム検証、プライベート IP 判定、リダイレクト時の再検証
- レスポンスサイズ制限と gzip 解凍後の再検査によりメモリ DoS を低減
- .env 読み込みで既存 OS 環境変数を保護する仕組み

Notes / Limitations / TODO
- pipeline.run_prices_etl など ETL 側は設計に沿った関数群を持つが、外部 quality モジュールや一部呼び出しフローの実装（例: 完全な ETL ワークフローの結合や追加ジョブのスケジューリング）は外部依存または拡張対象
- SQL の組み立てはチャンク用プレースホルダを動的生成しているため、大量データ時の長さ管理やパラメータ数上限に注意（チャンクサイズで制御済）
- このバージョンは「初期リリース（0.1.0）」であり、改善点（より詳細な品質チェック、監視/メトリクス、テストカバレッジ、エラーハンドリングの細分化など）は今後のリリースで対応予定

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 上述の SSRF / XML / レスポンスサイズ対策を実装

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

References
- パッケージバージョン: kabusys.__version__ == "0.1.0"