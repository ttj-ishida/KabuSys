# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはプロジェクトの主要な機能追加・挙動・安全対策などをコードベースから推測してまとめたものです。

## [0.1.0] - 2026-03-17

初回リリース。日本株の自動売買システム「KabuSys」の基盤機能を実装しています。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開バージョンは `0.1.0`。
  - サブパッケージの骨組み（data, strategy, execution, monitoring）を用意。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルートの探索は `.git` または `pyproject.toml` を基準に行う（CWD に依存しない）。
  - .env のパース関数（export 形式・クォート・インラインコメント対応）を実装。
  - Settings クラスを実装し、アプリケーション設定（J-Quants / kabuステーション / Slack / DB パス / 環境フラグ / ログレベル）をプロパティで提供。
    - 必須項目は未設定時に明示的にエラーを送出（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装（許容値を限定）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（JSON デコード、タイムアウト管理、ヘッダ設定）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象。
    - 429 の場合は `Retry-After` ヘッダを優先。
  - 認証トークン取得と自動リフレッシュ: `get_id_token()` と 401 受信時の一回限りのリフレッシュ処理。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - 全て ON CONFLICT による更新（DO UPDATE）で重複を排除
    - fetched_at を UTC で記録し、データの入手時刻をトレース可能に

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集・前処理・保存・銘柄紐付けの一連処理を実装。
  - 設計上の安全対策と実装概要:
    - defusedxml を使った XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストのプライベート/ループバック/IP 判定（DNS 解決して A/AAAA を検査）
      - リダイレクト時にスキーム/ホストを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）
    - レスポンスサイズ制限: MAX_RESPONSE_BYTES = 10MB、事前 Content-Length チェックと読み取り上限の二重チェックでメモリ DoS を防止
    - gzip 圧縮レスポンスの安全な解凍（解凍後サイズ再検査）
  - URL 正規化・トラッキングパラメータ除去:
    - utm_*, fbclid, gclid など既知トラッキングパラメータの除去
    - クエリパラメータをキーでソート、フラグメント除去
  - 記事 ID の生成:
    - 正規化 URL の SHA-256 の先頭 32 文字を記事 ID として利用（冪等性保証）
  - 前処理関数:
    - preprocess_text：URL 除去・空白正規化
    - _parse_rss_datetime：RFC 2822 形式のパース（失敗時は現在時刻で代替）
  - DB 保存と銘柄紐付け:
    - save_raw_news：チャンク分割 + トランザクション + INSERT ... RETURNING id で新規挿入記事 ID を返す（ON CONFLICT DO NOTHING）
    - save_news_symbols / _save_news_symbols_bulk：news_symbols テーブルへの紐付けをチャンク/トランザクションで保存し、実際に挿入された件数を返す
  - 銘柄コード抽出:
    - 4桁数字パターンから known_codes に含まれるもののみ抽出（重複排除）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataPlatform に基づく 3 層構造（Raw / Processed / Feature）と Execution 層を定義する DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを設定（頻出クエリパターンを想定）。
  - init_schema(db_path) による初期化（親ディレクトリの自動作成、:memory: 対応）と get_connection を公開。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL の基礎を実装（差分算出、backfill、品質チェックとの統合ポイント）。
  - ETLResult dataclass を定義し、取得数・保存数・品質問題・エラーを集約して返却。
  - 市場カレンダーを考慮したトレーディングデイ調整、テーブル最大日付取得ユーティリティ等を提供。
  - 個別 ETL ジョブ（例: run_prices_etl）を用意し、差分取得と jquants_client の save_* 関数を使った永続化を実行（backfill_days による前方再取得で API 後出し修正に対応）。
  - 品質チェックモジュール（quality）との連携ポイントを提供（重大度に応じた判定ロジックあり）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS 処理における以下のセキュリティ対策を追加:
  - defusedxml による安全な XML パース
  - SSRF 対策（スキーム検証、プライベート IP のブロック、リダイレクト検査）
  - レスポンスサイズ制限（Gzip 解凍後も検査）
- HTTP クライアントの例外ハンドリング、再試行ロジックにより外部 API 呼び出しの堅牢性を向上。

### 既知の注意点 / 挙動
- .env 自動読み込みはプロジェクトルート（.git/pyproject.toml）を基準に行うため、パッケージ配布後や特殊な配置では自動読み込みがスキップされる可能性があります。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って明示的に制御してください。
- jquants_client の再試行は最大 3 回。401 発生時はトークンを 1 回だけリフレッシュして再試行します（無限リフレッシュ回避）。
- DuckDB への保存は冪等性を重視しているため、重複レコードは ON CONFLICT により更新またはスキップされます。
- news_collector の URL 正規化は既知のトラッキングパラメータプレフィックスを想定して除去しますが、未知のパラメータには対応していない可能性があります。

---

今後のリリースでは戦略ロジック（strategy）、発注実行（execution）、モニタリング（monitoring）等の具体的実装、品質チェックモジュールの詳細化、テストカバレッジ強化、運用用 CLI/API の追加などが想定されます。要望や補足情報があれば追記してCHANGELOGを更新します。