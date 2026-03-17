CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース: KabuSys 0.1.0 を追加。
  - パッケージ構成: kabusys（サブパッケージ data, strategy, execution, monitoring を公開）。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 / config
  - Settings クラスを導入し、環境変数経由で各種設定を提供（J-Quants, kabuステーション, Slack, DBパス, ログレベル等）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、クォート内エスケープ、インラインコメント処理等対応）。
  - 環境値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を追加。
  - 必須環境変数未設定時に明示的なエラーを発生させる _require() を提供。

- データ取得: jquants_client
  - J-Quants API クライアントを実装:
    - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を提供。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行（リトライ）ロジック:
    - 指数バックオフ、最大 3 回（ネットワーク/サーバー系の 408/429/5xx を対象）。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンで自動リフレッシュして 1 回だけリトライ。
  - トークンキャッシュ: ページネーション間でトークン共有するモジュールレベルのキャッシュを実装（テスト可能な強制リフレッシュ対応）。
  - Look-ahead bias 対策: 取得時刻（fetched_at）を UTC で記録。
  - DuckDB への保存関数を実装（冪等性のため INSERT ... ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar().
  - 型変換ユーティリティ: _to_float(), _to_int() — 安全な変換と不正値処理。

- ニュース収集: news_collector
  - RSS フィード収集モジュールを実装。
    - fetch_rss() で RSS を取得し、記事（id, datetime, source, title, content, url）を抽出。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - preprocess_text(): URL 除去・空白正規化を実行。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等に対する防御）。
    - SSRF 対策: リダイレクト先のスキーム検証およびプライベートアドレス判定を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカルであれば拒否する検査（_is_private_host）。
    - HTTP/HTTPS 以外のスキーム拒否、受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリDoS対策、gzip 解凍後サイズチェック。
  - DB保存:
    - save_raw_news(): チャンク分割 + トランザクション + INSERT ... ON CONFLICT DO NOTHING RETURNING を用いて実際に挿入された記事IDを返す。
    - save_news_symbols() / _save_news_symbols_bulk(): 記事と銘柄コードの紐付けを一括保存（同様に RETURNING を利用して挿入数を正確に算出）。
  - 銘柄抽出: extract_stock_codes() によりテキスト中の 4 桁銘柄コードを known_codes でフィルタして抽出。
  - 統合ジョブ: run_news_collection() で複数ソースからの収集 → 保存 → 新規記事に対する銘柄紐付けを実行。個々ソースは独立して失敗耐性あり。

- スキーマ管理: data.schema
  - DuckDB スキーマ初期化モジュールを追加。
    - Raw / Processed / Feature / Execution の多層テーブル定義を提供（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, orders, trades, positions, 等）。
    - データ整合性チェック用の制約（CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
    - 頻出クエリ向けのインデックスを自動作成。
    - init_schema(db_path) でディレクトリ作成→接続→DDL/インデックス適用を行い、get_connection() で既存 DB に接続可能。

- ETL パイプライン: data.pipeline
  - ETLResult データクラスを導入（取得件数、保存件数、品質問題リスト、エラーリスト等を保持）。
  - 差分更新ヘルパー: get_last_price_date(), get_last_financial_date(), get_last_calendar_date() を実装。
  - 市場カレンダー補助: _adjust_to_trading_day() により非営業日を直近営業日に調整するロジックを追加。
  - run_prices_etl(): 差分更新ロジック（最終取得日からの backfill、デフォルト backfill_days=3）と jquants_client を呼ぶ ETL ワークフローを実装（取得→保存→ログ出力）。
  - 設計方針: 差分更新、バックフィルによる後出し修正吸収、品質チェックの呼び出し（quality モジュール参照）を想定した構成。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサと HTTP クライアント周りに対して SSRF、XML Bomb、Gzip Bomb、受信サイズ制限、スキーム検証など複数の防御を実装。

Notes / Known
- ETL・品質検査・実運用向けの設定（Slack 通知や kabuAPI 実行周り、strategy/execution の具象実装）はフレームワークとして整備済みで、個別戦略や注文ロジックは今後の実装対象。
- news_collector と jquants_client は外部 API/ネットワークに依存するため、テスト時はモック差し替えが容易な設計（例: _urlopen、id_token 注入など）になっている。

---

今後の予定（例）
- strategy / execution の具体的な売買ロジック、発注フローの実装。
- 品質チェックモジュール（quality）の詳細実装および ETL への統合強化。
- モニタリング / アラート（Slack 統合）の追加強化。

(End of changelog)