# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

リリース日や機能はコードベースから推測して記載しています。

## [0.1.0] - 2026-03-17

初回公開リリース。

### 追加（Added）
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に指定。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（OS 環境変数 > .env.local > .env の優先順位）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - プロジェクトルート検出機能: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサ実装: コメント・export プレフィックス・クォート・エスケープ処理などをサポート。
  - Settings クラス実装: J-Quants、kabuAPI、Slack、DBパス、環境（development/paper_trading/live）等のプロパティを提供。値検証（env と log_level の許可値チェック）を含む。
  - パスプロパティは Path 型で返す（DuckDB/SQLite の既定パス含む）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - データ取得機能: 株価日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、JPX マーケットカレンダー（fetch_market_calendar）。
  - 認証: refresh token から id_token を取得する get_id_token を実装。呼び出し/ページネーション間で id_token キャッシュを共有。
  - レート制御: 固定間隔スロットリング (_RateLimiter) により 120 req/min を順守。
  - リトライロジック: 指数バックオフ・最大 3 回・HTTP 408/429/5xx に対する再試行。429 の場合は Retry-After を優先利用。
  - 401 対応: 401 受信時に id_token を自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - JSON レスポンスのデコード検証およびタイムアウト設定。
  - DuckDB への保存関数（保存は冪等）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE を用いた挿入/更新。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE。
  - データ整形ユーティリティ: _to_float / _to_int（型安全な変換とバリデーション）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存する機能を実装（fetch_rss, save_raw_news）。
  - セキュリティ対策:
    - XML パースに defusedxml を利用して XML Bomb 等に対処。
    - SSRF 対策: リダイレクト先のスキーム・ホスト事前検証、プライベートIP/ループバック/リンクローカル/マルチキャストを拒否。_SSRFBlockRedirectHandler と _is_private_host を実装。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後チェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）。記事ID は正規化 URL の SHA-256 ハッシュ先頭32文字で生成（_make_article_id）して冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）機能（preprocess_text）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDのみを返す。チャンク分割・単一トランザクションでの実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コード (news_symbols) の紐付けを一括で保存。ON CONFLICT DO NOTHING と RETURNING を使用して挿入数を正確に取得。
  - 銘柄コード抽出: 正規表現による 4 桁数字抽出と既知銘柄セットによるフィルタリング（extract_stock_codes）。
  - 統合ジョブ run_news_collection を実装し、複数 RSS ソースを独立に処理。既知銘柄が与えられれば新規記事に対して銘柄紐付けを行う。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - データレイヤ構成に基づくテーブル定義を実装（Raw / Processed / Feature / Execution）。主要テーブルを網羅:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム定義には CHECK 制約や NOT NULL、外部キー制約を含む。
  - 代表的なインデックスを作成（頻繁なクエリパターンに対するインデックス）。
  - init_schema(db_path) を実装: 必要に応じて親ディレクトリを作成し、DDL とインデックスを実行して接続を返す（冪等）。get_connection() も提供。

- ETL パイプライン基礎（src/kabusys/data/pipeline.py）
  - ETL の設計方針と差分更新ロジックの実装（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - ETLResult データクラスを追加: 各処理結果・品質問題・エラーの集約と to_dict 出力。
  - 市場カレンダー補助: 非営業日の場合に最も近い過去の営業日に調整する _adjust_to_trading_day。
  - run_prices_etl の骨組みを実装（差分計算、backfill_days による再取得、jquants_client の fetch/save を連携）。最小データ日付として 2017-01-01 を定義。
  - パイプラインは id_token 注入可能でテスト容易性を確保。品質チェックモジュール（quality）との統合点を想定。

### 改善（Changed）
- DB 操作での冪等性を重視した設計:
  - raw / processed テーブルへの INSERT は ON CONFLICT を用いて重複や再取得に耐えるように実装。
  - news_collector の記事ID生成・URL 正規化により、同一記事の重複保存を防止。

- ネットワーク呼び出しの堅牢化:
  - タイムアウト・リトライ・レート制御・429 Retry-After の尊重など運用面の配慮を実装。

- セキュリティと安全性の強化:
  - defusedxml, SSRF 検査、レスポンスサイズ制限、スキーマ検証などにより外部入力に対する耐性を向上。

### 修正（Fixed）
- （初期リリースのため過去のバグ修正履歴はなし。実装上の注意点や例外処理は各モジュール内に組み込まれている。）

### セキュリティ（Security）
- XML パースに defusedxml を導入し、XML ベースの攻撃を軽減。
- RSS フェッチでのリダイレクト検査とプライベートアドレス検出により SSRF リスクを低減。
- レスポンスサイズと gzip 解凍後のサイズチェックで DoS（メモリ爆発）対策を導入。

### 開発・テスト向け
- 設定読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト環境向け）。
- news_collector._urlopen や jquants_client の id_token 注入など、ネットワーク依存部のモック差し替えを想定した設計。

---

注記:
- 本 CHANGELOG は提供されたコード内容から推測して作成しています。実運用でのリリースノートとして使用する際は、実際のコミット / PR / 変更履歴に基づき追記・修正してください。