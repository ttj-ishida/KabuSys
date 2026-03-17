# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトの初期リリースを記録しています。

全てのバージョンは semver に従います。  

## [0.1.0] - 2026-03-17

初期公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - src/kabusys 以下にモジュール構成（data, strategy, execution, monitoring）を用意。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み（プロジェクトルートを .git または pyproject.toml で検出）を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの取り扱いに対応。
  - 必須設定取得用の _require() と、環境値の検証（KABUSYS_ENV, LOG_LEVEL）実装。
  - DBパス（DuckDB/SQLite）や各種APIトークン等のプロパティを提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を追加（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、有効なステータス: 408/429/5xx）を実装。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライ。
  - id_token のモジュールレベルキャッシュを実装しページネーション間で共有。
  - DuckDB へ冪等に保存する save_* 関数を追加（INSERT ... ON CONFLICT DO UPDATE）。
  - データ取り扱いの補助関数（_to_float, _to_int）を追加し安全に変換。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集する fetch_rss、save_raw_news、save_news_symbols、run_news_collection を実装。
  - 記事IDを正規化 URL の SHA-256（先頭32桁）で生成し冪等性を確保。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）を実装。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - DNS 解決してプライベート/ループバック/リンクローカル/マルチキャストを検出し拒否。
    - リダイレクト時に検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再検査を実装（メモリ DoS / gzip bomb 対策）。
  - 受信ヘッダの Content-Length チェック、チャンク読み取りによる超過判定。
  - raw_news への INSERT はチャンク分割してトランザクション内で実施し、INSERT ... RETURNING で実際に挿入されたIDを返す。
  - news_symbols の一括保存機能（重複除去・チャンク挿入）を実装。
  - 本文からの銘柄コード抽出（四桁数字）と既知銘柄セットとの突合せ機能を実装。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づいたスキーマを追加。
    - Raw layer（raw_prices, raw_financials, raw_news, raw_executions）
    - Processed layer（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
    - Feature layer（features, ai_scores）
    - Execution layer（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - テーブル作成順・外部キーを考慮した DDL を提供。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ自動作成と idempotent な初期化を行う。get_connection で既存 DB へ接続可能。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL の骨子を実装（run_prices_etl 等）。
  - 最終取得日からの差分取得、backfill_days による再取得（後出し修正吸収）に対応。
  - ETL 実行結果を表す ETLResult データクラスを実装（品質チェック問題・エラーの集約、JSON 変換対応）。
  - テーブル存在チェック、最大日付取得、営業日調整のヘルパーを実装。
  - jquants_client の save_* を使った冪等保存を前提に設計。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- XML パーシングに defusedxml を使用して XML 関連攻撃（XML Bomb 等）に対処。
- RSS フェッチ時に SSRF 対策を多数導入（スキーム制限、プライベートアドレス検出、リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する protected 機構を導入。必要に応じて自動ロードを無効化可能。

### 既知の制限 / 注意事項 (Known issues / Notes)
- jquants_client の API レート制御は固定間隔スロットリング（単純な wait ベース）で実装しているため、極端な同時並列呼び出しパターンでは別途プロセス間の調整が必要になる可能性があります。
- RSS フィードの pubDate パースに失敗した場合は警告ログを出して現在時刻で代替します（raw_news.datetime は NOT NULL の設計による）。
- 現在実装されている ETL の品質チェック機能（quality モジュール）は呼び出し側での連携を想定しています（quality モジュール本体は別途実装を想定）。

### 将来的な改善案（検討中）
- レートリミッタをプロセス/分散レベルで共有できる仕組み（Redis 等）に変更し、複数ワーカーでの協調を実現する。
- RSS パーシングの追加フィールド（メディア、カテゴリ等）や言語解析による銘柄抽出の強化。
- ETL の完全自動スケジューリングと監視ダッシュボード（monitoring モジュールの拡充）。

---

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際の設計意図やドキュメントが存在する場合はそちらに合わせて更新してください。）