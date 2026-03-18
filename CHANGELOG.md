# Changelog

すべての重要な変更点は Keep a Changelog の方針に従って記載しています。  
なお、この CHANGELOG は提示されたコードベースの内容から実装機能・設計意図を推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。

### Added
- パッケージ構成
  - パッケージ名 kabusys を導入。公開 API として data, strategy, execution, monitoring を想定（__all__ に登録）。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local からの自動読み込み機能を実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から探索し、自動ロードの可否を決定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パースの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - インラインコメントの扱い（クォート有無での判定）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルのプロパティを定義。必須キー未設定時は ValueError を送出。
  - DUCKDB_PATH / SQLITE_PATH のデフォルトや Path 型への正規化を提供。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）と便利プロパティ (is_live, is_paper, is_dev)。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダーの取得関数を実装（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
  - 認証とトークン管理:
    - get_id_token によるリフレッシュトークン→IDトークン取得（POST /token/auth_refresh）。
    - モジュールレベルでの ID トークンキャッシュを保持し、ページネーション間で共有。
    - 401 受信時は自動でトークンを1回リフレッシュして再試行する仕組みを実装（無限再帰防止のため allow_refresh フラグあり）。
  - レート制御・リトライ:
    - 固定間隔スロットリング _RateLimiter（120 req/min 相当）を実装して API レートを順守。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/500系を対象）。429 の場合は Retry-After ヘッダを尊重。
    - ネットワークエラー（URLError, OSError）もリトライ対象。
  - データ保存:
    - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。いずれも冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead バイアスを防止。
  - 型変換ユーティリティ:
    - _to_float / _to_int を実装。文字列/空値/不正値の扱いを明確化（小数を伴う int 値は None を返す等）。
  - ロギングを充実させ、API 呼び出し数や保存件数を記録。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し DuckDB の raw_news / news_symbols 等へ保存する実装を追加。
  - 主な機能・設計:
    - デフォルト RSS ソース定義（例: Yahoo Finance ビジネス RSS）。
    - 取得サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設定し、メモリ DoS を防止。
    - gzip 圧縮の解凍と Gzip-bomb に対するサイズチェック。
    - defusedxml を用いた安全な XML パース（XMLBomb 等対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - 取得前にホストがプライベート/ループバック/リンクローカルでないかを判定（IP 直接判定・DNS 解決して A/AAAA レコードをチェック）。
      - リダイレクト時にスキームとホストを検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - 記事 ID の生成:
      - URL を正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）して SHA-256 を取り、先頭 32 文字を記事IDとすることで冪等性を担保。
    - テキスト前処理（URL 削除や空白正規化）と pubDate の堅牢なパース（RFC2822 準拠、失敗時は現在時刻で代替）。
    - DB 保存:
      - save_raw_news はチャンク単位のバルク INSERT（INSERT ... RETURNING）を採用し、実際に挿入された記事IDのリストを返す。トランザクション内で処理し、失敗時はロールバック。
      - save_news_symbols と内部の _save_news_symbols_bulk は記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING で冪等に保存。
    - 銘柄抽出:
      - 4 桁数字パターンを候補として抽出し、known_codes に存在するもののみを採用（重複排除）。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataPlatform に基づく多層スキーマを定義（Raw / Processed / Feature / Execution レイヤ）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK 等）を付与し、データ整合性を強化。
  - よく使われるクエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ作成（必要時）→テーブル/インデックス作成（冪等）を実行。
  - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - 差分更新を行う ETL の骨格を実装。
  - ETLResult dataclass を追加し、取得数・保存数・品質問題・エラー一覧等を集約可能にした。
  - テーブル存在チェックや最大日付取得ユーティリティ（_table_exists、_get_max_date）を実装。
  - トレーディング日調整ヘルパー（_adjust_to_trading_day）を実装。market_calendar が空でもフォールバック動作。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl により差分取得ロジックを実現（最終取得日の backfill を考慮して再取得）。取得 → jq.save_daily_quotes による保存 → 結果をログ出力。

### Security
- RSS/HTTP 関連のセキュリティ対策を多数実装
  - defusedxml による XML パースで XML Bomb 等を防止。
  - レスポンスサイズ制限と gzip 解凍後の上限チェックでメモリ DoS を軽減。
  - URL スキーマチェック、プライベート IP/DNS 検査、リダイレクト時の検証で SSRF リスクを低減。

### Performance & Reliability
- API 呼び出しのレート制御（120 req/min）とリトライ（指数バックオフ）により外部 API 依存処理の安定性を向上。
- DuckDB へのバルク挿入・チャンク分割・トランザクション管理で大量データ挿入時のオーバーヘッドを低減。
- ページネーション時の ID トークンキャッシュ共有により認証の再取得を最小化。

### Logging / Observability
- 各種処理において取得件数・保存件数・警告ログを追加し、運用上の把握を容易に。
- ETLResult の to_dict により品質問題やエラー情報を構造化して出力可能。

### Known limitations / Notes
- strategy / execution / monitoring モジュールの詳細実装はこのリポジトリ断片では未提示（各レイヤのインターフェース準備はされている）。
- quality モジュール（データ品質チェック）の実装は参照されているが、今回提示されたコード断片では詳細は未確認。
- run_prices_etl や他 ETL ジョブは引数により id_token を注入可能でテスト容易性を考慮している（実装の続きや追加の ETL ジョブは今後の拡張想定）。

---

この CHANGELOG は提示コードから読み取れる実装点・設計方針を要約したものです。追加でリリース日を固定したい、あるいは未公開の変更履歴（バグ修正や内部リファクタ）を反映したい場合は、該当部分のソース差分あるいはコミットログを提示してください。