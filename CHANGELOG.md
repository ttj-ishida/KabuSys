# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
現在のパッケージバージョン: 0.1.0

注: 以下は提示されたコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース。kabusys 名前空間を導入。
  - src/kabusys/__init__.py にてバージョン管理と公開サブパッケージを定義。
- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存での .env 自動読み込みを実現。
  - 読み込み順序: OS環境変数 > .env.local > .env。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 行パーサーはコメント、`export KEY=val` 形式、クォートとバックスラッシュエスケープ、インラインコメント等に対応。
  - 必須設定取得ヘルパー `_require()` と Settings クラスで J-Quants / kabu API / Slack / DB パス / モード（development/paper_trading/live）等をプロパティで提供。
  - LOG_LEVEL、KABUSYS_ENV の検証ロジックを実装（許容値チェック）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得用 API 呼び出しを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、ステータス 408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ（モジュールレベル）を実装。
  - ページネーション対応（pagination_key を用いた繰り返し取得）。
  - 取得データ保存関数（save_*）は DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）し、fetched_at を UTC で記録して look-ahead bias を抑制。
  - データ変換ユーティリティ `_to_float`, `_to_int` を提供（不正値は None を返す。float文字列→int変換時の丸め回避ロジック等）。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード取得・パース・前処理・DB 保存を行う ETL（raw_news / news_symbols 登録）。
  - デフォルト RSS ソース（例: Yahoo Finance）を定義。
  - URL 正規化（トラッキングパラメータ削除、鍵順ソート、フラグメント除去）、SHA-256（先頭32文字）による記事ID生成により冪等性を担保。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を緩和。
  - SSRF 対策: URL スキーム検証（http/https 限定）、ホストがプライベート/ループバック/リンクローカルか判定して拒否、リダイレクト時の検査ハンドラを導入。
  - レスポンス読み取り上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査でメモリDoS/Gzip Bomb を防止。
  - テキスト前処理（URL除去・空白正規化）、タイトル/本文統合による銘柄コード抽出（4桁数字、known_codes 参照）。
  - DuckDB への保存はチャンク INSERT、トランザクション管理、INSERT ... RETURNING による実挿入数の取得を行う。重複は ON CONFLICT DO NOTHING でスキップ。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各カラムに対する型と CHECK 制約（負値禁止、サイズチェック、ENUM的な制約等）を定義。
  - 外部キーと参照整合性（ON DELETE 挙動）を設定。
  - 性能向上のためのインデックス一覧を定義（頻出クエリパターンに基づく）。
  - init_schema(db_path) で親ディレクトリの自動作成、DDL 実行、インデックス作成を行い、DuckDB 接続を返す。get_connection() で既存 DB への接続を提供。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新ロジック: DB の最終取得日を参照して差分（および backfill_days による再取得）を自動算出。
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）や J-Quants の最小データ開始日定義。
  - ETL 実行結果を格納する ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー一覧など）。
  - テーブル存在チェック・最大日付取得ユーティリティを提供。
  - run_prices_etl の実装（差分算出→fetch_daily_quotes→save_daily_quotes、保存件数の戻り値）。

### Security
- XML パースに defusedxml を採用して XML 関連の脆弱性（XML Bomb 等）を緩和。
- RSS フェッチ時の SSRF 緩和: スキーム検証、プライベートIP/ループバック検出、リダイレクト検査ハンドラを実装。
- ネットワーク取得時のレスポンスサイズ上限や gzip 解凍後のサイズ検査によりメモリ DoS / Gzip Bomb を防止。
- .env 読み込みは OS 環境変数の保護（protected set）を行い、override フラグで上書き挙動を制御。

### Fixed / Improved
- .env パーサーでの次の改善点を実装:
  - export プレフィックス対応、クォート内バックスラッシュエスケープの適切処理、インラインコメントの扱い、キー空白トリム等をサポートして堅牢性を向上。
- jquants_client の HTTP エラー時リトライにおいて、429 の Retry-After ヘッダを優先して待機時間を決定するよう改善。
- jquants_client の JSON デコード失敗時に詳細メッセージを含めて例外を投げるよう改善しデバッグを容易化。
- news_collector の RSS パースで channel/item が無い場合のフォールバックと適切なログ出力を追加。

### Removed
- （なし）

### Notes / Known limitations
- 現在の実装は主にデータ取得・保存・初期 ETL を対象としており、実際の発注実行ロジック、モニタリング統合、戦略モジュールはパッケージに名前空間として存在するが（strategy/, execution/, monitoring/）、今回提示されたコードにはそれらの詳細実装は含まれていません。
- J-Quants API の利用には有効なリフレッシュトークン等の環境変数設定が必要。未設定時は Settings._require による ValueError が発生します。
- DuckDB の DDL/制約は設計ドキュメントに基づく想定で定義されています。運用要件に応じてスキーマやインデックスの追加・調整を推奨します。

---

参照: Keep a Changelog (https://keepachangelog.com/) に準拠。