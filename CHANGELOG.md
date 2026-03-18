CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
このプロジェクトではセマンティックバージョニングを採用しています。

[Unreleased]
------------

- 既知の制限 / 次回作業予定
  - run_prices_etl の戻り値周りに未完（現状ソースの末尾が一部欠落しており、(fetched, saved) の両値を返す意図が見えるが実装が途中の可能性あり）。次リリースで ETL の完了・統合テストを行う予定。
  - strategy/execution パッケージはプレースホルダ（__init__.py が空）となっているため、戦略・発注ロジックの実装が必要。
  - quality モジュール（参照はあるが実装が別途必要）との統合テスト・品質チェックルール拡充を予定。

0.1.0 - 2026-03-18
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎実装を追加。
- パッケージ構成
  - kabusys パッケージを提供。__version__ = "0.1.0"。
  - サブパッケージ: data, strategy, execution, monitoring（strategy/execution は初期プレースホルダ）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用フラグ）。
  - .env パーサーは export KEY=val 形式、引用符付き値、行内コメントを考慮した堅牢な解析に対応。
  - 設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得（未設定時は ValueError）。
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request、get_id_token）。
  - 機能:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ (fetch_financial_statements)
    - JPX マーケットカレンダー (fetch_market_calendar)
  - 設計特徴:
    - レート制限: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - リトライ: 指数バックオフで最大 3 回、408/429/5xx を対象。
    - 401 受信時はリフレッシュ（1 回のみ）→ id_token を自動更新して再試行。
    - ページネーション対応（pagination_key を使用）。
    - fetched_at を UTC タイムスタンプで記録し Look-ahead バイアスのトレースを可能に。
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（冪等化: ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し不正値に対処。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得・正規化・DB 保存のフルワークフローを実装。
  - 主な機能:
    - fetch_rss: RSS を取得して記事リストを返す（defusedxml を使った安全なパース）。
    - URL 正規化: トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - セキュリティ対策:
      - SSRF 防止: リダイレクト先のスキーム検査、プライベートIP/ループバック/リンクローカルのブロック（DNS 解決した A/AAAA レコード検査）。
      - 許可スキームは http/https のみ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - defusedxml による XML 攻撃対策。
    - テキスト前処理 (preprocess_text): URL 除去・空白正規化。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて新規挿入 ID を返す（チャンク & 単一トランザクション）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING、RETURNING を利用）。
    - 銘柄コード抽出: 4桁数字パターンから既知銘柄集合に基づいて抽出する extract_stock_codes。
    - run_news_collection: 複数ソースを巡回して収集・保存・銘柄紐付けを実行（個々のソースは独立してエラーハンドリング）。
  - テストフック:
    - _urlopen はモック可能（テスト時に置き換え可能）として設計。
- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）テーブル定義を実装。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・チェック（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を指定。
  - インデックス定義（頻出クエリに対する複数インデックス）。
  - init_schema(db_path): DB ファイルの親ディレクトリ自動作成、DDL/インデックスを順序を考慮して実行して接続を返す（冪等）。
  - get_connection(db_path): 既存 DB への接続を返す（初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - ETL の結果を格納する ETLResult dataclass を追加（品質問題とエラーの集約、シリアライズ用 to_dict）。
  - 差分更新ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - run_prices_etl: 差分取得ロジック（最終取得日から backfill_days 分さかのぼって再取得）を実装（backfill_days のデフォルトは 3 日）。
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日を直近の営業日に調整、最大 30 日遡り）。
  - 設計方針:
    - 差分更新をデフォルトとし、API の後出し修正を backfill_days で吸収。
    - 品質チェック（quality モジュール）を呼び出し、致命的問題があっても収集は継続。呼び出し元が措置を判断。
    - id_token を引数注入可能にしてテスト容易性を向上。
- その他
  - ロギングメッセージを多数追加し動作確認や監査を容易に。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間でトークンを共有しリクエスト数を削減）。

Security
- RSS ニュース収集において SSRF・XML攻撃・Gzip bomb 対策を導入（_SSRFBlockRedirectHandler、defusedxml、受信サイズ上限等）。
- .env パーサーは行内コメント・引用符・エスケープに対応し、誤解析による環境漏洩を低減。

Fixed
- N/A（初回公開のため既知のバグ修正履歴なし）。

Deprecated
- N/A

Removed
- N/A

Notes
- このリリースは「データ収集」と「DB スキーマ整備」を中心とした初期実装です。戦略評価・発注ロジック・監視機能は次フェーズで追加予定です。
- テストについて:
  - ネットワーク呼び出しや外部 API に依存する箇所はフック（_urlopen のモック等）を用いてユニットテストが可能な設計になっています。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境依存の自動 .env 読み込みを抑制できます。

配布・インストール
- パッケージバージョン: 0.1.0
- 主要依存（コード上の参照）:
  - duckdb
  - defusedxml

ライセンス・貢献
- 貢献ガイド・ライセンスはリポジトリのルート（pyproject.toml 等）を参照してください（パッケージ内では未定義のため、外部ファイルに依存）。

----- 

以上が本コードベースから推測して作成した CHANGELOG.md（Keep a Changelog 形式）です。必要であれば各項目をさらに詳細化（関数単位の変更ログ、SQL スキーマ差分、想定 API エラーケースの一覧など）します。どの程度の詳細が必要か教えてください。