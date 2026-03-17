# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装します。主な追加点と設計方針を以下に示します。

### 追加 (Added)
- パッケージ構成
  - `kabusys` パッケージの骨格を追加。公開サブパッケージは data, strategy, execution, monitoring を想定。
- 環境設定
  - `kabusys.config.Settings` を追加し、環境変数・.env ファイルから設定値を取得する仕組みを提供。
  - プロジェクトルート自動検出（`.git` または `pyproject.toml`）に基づく .env 自動読み込み機能を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス・クォート文字列・インラインコメントを考慮した堅牢な実装を提供。
  - 必須環境変数取得用の `_require()` を実装（設定不足時は ValueError を送出）。
  - 環境名（development, paper_trading, live）およびログレベルのバリデーションを実装。
- J-Quants API クライアント
  - `kabusys.data.jquants_client` を追加。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）を実装。
  - 冪等性とページネーション対応のデータ取得関数を追加:
    - fetch_daily_quotes: 株価日足（OHLCV）のページネーション対応取得
    - fetch_financial_statements: 財務（四半期 BS/PL）
    - fetch_market_calendar: JPX マーケットカレンダー
  - リトライ戦略（指数バックオフ、最大3回、HTTP 408/429/5xx をリトライ対象）を実装。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）を実装。`get_id_token` によるリフレッシュ実装あり。
  - DuckDB への保存関数（冪等）を追加:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE による更新）
  - 取得時刻（fetched_at）は UTC にて記録し、Look-ahead Bias のトレーサビリティを確保。
- ニュース収集モジュール
  - `kabusys.data.news_collector` を追加。RSS フィードから記事収集→前処理→DuckDBに保存を行う。
  - セキュリティと堅牢性：
    - defusedxml を使用した XML パース（XML Bomb への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト時にホストがプライベートアドレスでないことを検査。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリDoSを防止。gzip 解凍後もサイズ検査。
    - トラッキングパラメータ（utm_*, fbclid 等）を除去する URL 正規化。記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - HTTP ヘッダに User-Agent と Accept-Encoding を設定。
  - DB 保存の工夫:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING を用いて実際に挿入された記事IDを返す（チャンク挿入、トランザクションまとめ）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入して保存数を正確に取得。
  - テキスト前処理（URL除去・空白正規化）、RSS pubDate の堅牢なパース（UTC 正規化）を実装。
  - 既定の RSS ソースに Yahoo Finance のビジネスカテゴリを追加（DEFAULT_RSS_SOURCES）。
  - 銘柄コード抽出ユーティリティ（4桁数字＋既知銘柄セットフィルタ）を実装。
  - 統合収集ジョブ run_news_collection を実装（ソース単位で失敗を隔離し継続）。
- DuckDB スキーマ
  - `kabusys.data.schema` に DuckDB のスキーマ定義と初期化関数を実装。
  - Raw / Processed / Feature / Execution 層のテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 適切なチェック制約（CHECK）、PRIMARY KEY、外部キー、インデックスを定義（頻出クエリパターンに対するインデックスを含む）。
  - init_schema(db_path) で必要な親ディレクトリを自動作成してテーブルとインデックスを作成する初期化処理を提供。get_connection() で既存DBへの接続を提供。
- ETL パイプライン
  - `kabusys.data.pipeline` を追加。差分更新ロジック、backfill（デフォルト3日）を備えた ETL 実装の下地を提供。
  - ETLResult データクラスを追加し、各 ETL ジョブの取得数・保存数・品質問題・エラーを集約可能に。
  - テーブル存在チェック、最大日付取得ユーティリティを実装。
  - 価格データ差分 ETL run_prices_etl を追加（date_from 自動算出、backfill 対応、fetch→save の流れ）。
  - 市場カレンダーの先読み設定（_CALENDAR_LOOKAHEAD_DAYS = 90）やデータ開始日定数（_MIN_DATA_DATE = 2017-01-01）などを設定。

### 変更 (Changed)
- ロギングの充実:
  - 各主要処理（fetch/save/ETL/run_news_collection 等）で情報・警告・例外ログを追加して監査性とデバッグ性を向上。
- 型アノテーションとドキュメントストリング:
  - 多くの関数に型注釈と docstring を追加し、テスト容易性と可読性を向上。

### 修正 (Fixed)
- API 呼び出しの堅牢化:
  - JSON デコード失敗時に詳細メッセージを含めて RuntimeError を送出するように改善。
  - ネットワークエラーと HTTP エラーのリトライハンドリングを明確化（429 の Retry-After ヘッダ尊重など）。
- ニュース収集の堅牢化:
  - gzip 解凍や XML パース失敗時に安全にスキップして収集ジョブ全体を継続するよう調整。
  - リダイレクト先のスキーム/ホスト検査を導入し SSRF を低減。

### セキュリティ (Security)
- XML パースに defusedxml を採用して XML 外部エンティティや XML Bomb に対する防御を実現。
- RSS フェッチで SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト時検査）を導入。
- .env 読み込みで OS 環境変数上書き保護（protected set）を実装。

### 既知の制限 / 今後の課題 (Known issues / Future)
- strategy、execution、monitoring パッケージは初期骨格のみ（空の __init__.py）で、戦略ロジックや発注実行・監視機能は今後実装予定。
- 品質チェックモジュール（kabusys.data.quality）は参照されているが本リリース内に具体実装が含まれていない（pipeline は設計に沿って品質チェックを呼び出す想定）。
- 一部のユニットテスト・統合テストは未実装。特にネットワークまわり・DBトランザクションの模擬テストが今後必要。
- パッケージ化／配布（wheel や CI パイプライン）の設定は別途整備予定。

---

以上が本リリース（0.1.0）の変更点です。さらに詳細な設計や使用法は各モジュールの docstring を参照してください。