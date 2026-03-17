# Keep a Changelog

すべての変更は逆順（新しいものが上）で記載します。  
このファイルは Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎機能を実装。
  - パッケージルート: `kabusys`（__version__ = 0.1.0）。
  - 主要モジュール群: data, strategy, execution, monitoring（未実装箇所は空イニシャライザを用意）。
- 設定管理 (`kabusys.config`)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須設定値取得時に未設定だと例外を発生させる `_require()` を提供。
  - 環境変数の検証:
    - KABUSYS_ENV は `development` / `paper_trading` / `live` を許容。
    - LOG_LEVEL は `DEBUG/INFO/WARNING/ERROR/CRITICAL` を許容。
  - 主要設定プロパティを `Settings` クラスとして公開（例: `settings.jquants_refresh_token`、`settings.kabu_api_password`、`settings.slack_bot_token`、`settings.duckdb_path` など）。
- データ層: J-Quants クライアント (`kabusys.data.jquants_client`)
  - J-Quants API からのデータ取得（株価日足 / 財務データ / マーケットカレンダー）を実装。
  - 設計上の特徴:
    - API レート制限遵守（120 req/min）: 固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライ対象。
    - 401 時はリフレッシュトークンで自動的に ID トークンを更新して1回リトライ。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias をトレース可能に。
    - DuckDB への保存は冪等性を確保（INSERT ... ON CONFLICT DO UPDATE）。
  - ユーティリティ変換関数: 安全に float / int に変換する `_to_float` / `_to_int`。
- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事収集・前処理・DB保存までの一連処理を実装。
  - 特徴:
    - デフォルト RSS ソースに Yahoo Finance を登録。
    - 記事ID は正規化した URL の SHA-256 の先頭32文字を使用（トラッキングパラメータ除去後）。
    - XML パースに `defusedxml` を使用して XML Bomb 等の攻撃を防御。
    - SSRF 対策:
      - 許可スキームは http/https のみ。
      - リダイレクト時にスキームとホストを検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否（DNS 解決された全 A/AAAA を検査）。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後サイズチェック（GZip bomb 対策）。
    - メモリ・DoS 対策として読込上限を設定。
    - テキスト前処理で URL 除去・空白正規化。
    - DuckDB への保存はチャンク化・トランザクション化し、INSERT ... RETURNING を使って実際に挿入された ID/件数を返す（冪等: ON CONFLICT DO NOTHING）。
    - 記事と銘柄の紐付け機能（news_symbols テーブルへ一括保存）。
    - 銘柄コード抽出は正規表現で 4 桁数字を検出し、known_codes によるフィルタリングを行う。
- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層に分けたテーブル定義を実装。
  - テーブル一覧（一部抜粋）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 頻繁に使われるクエリ向けにインデックスを作成。
  - init_schema(db_path) でディレクトリ作成→接続→DDL 実行して初期化（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン基礎 (`kabusys.data.pipeline`)
  - ETL 実行結果を表現する `ETLResult` データクラスを提供（品質問題とエラー一覧を保持、辞書化メソッドあり）。
  - 差分取得ヘルパー:
    - DB の最終取得日を取得する関数（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 非営業日調整 `_adjust_to_trading_day`（市場カレンダー参照、最大30日遡るフォールバックも実装）。
  - run_prices_etl() の骨組みを実装:
    - 最終取得日に基づき差分（backfill_days=3 をデフォルト）を再取得して保存。
    - jquants_client の fetch/save を利用して取得→保存（冪等）。
    - ETL の設計方針やバックフィル、品質チェックの呼び出し設計を明記。

### 修正 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- RSS パーシングで defusedxml を利用して XML ベースの攻撃を軽減。
- ニュース取得における SSRF 防御:
  - URL スキーム検証（http/https のみ許可）。
  - リダイレクト先に対する事前検証（スキーム・プライベートIPチェック）。
  - DNS 解決した各アドレスのプライベート/ループバック判定。
- ネットワーク読み込みのサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズチェックを導入。
- J-Quants クライアントはレート制限とリトライロジックを採用し、過負荷や API 制限に対する耐性を向上。

### 既知の制限・注意点 (Known issues / Notes)
- strategy / execution / monitoring の主要ロジックはこのリリースではスケルトン（パッケージ初期化子のみ）として提供。発注ロジックや戦略本体は別途実装が必要。
- run_prices_etl() など ETL 関連は設計と主要処理を実装しているが、品質チェックモジュール（kabusys.data.quality）の具体的な実装依存部分やその他補助処理は外部実装を前提としている。
- DuckDB スキーマは強めの制約（CHECK／FOREIGN KEY）を入れているため、既存データをマイグレーションする場合は注意が必要。

---

（以降のバージョンや修正はここに追記します）