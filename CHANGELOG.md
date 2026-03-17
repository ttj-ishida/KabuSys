CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

Unreleased
----------

（現在の未リリース変更はありません）

[0.1.0] - 2026-03-17
-------------------

初期リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。

### Added
- パッケージ構成を追加
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用途）。
  - .env パーサー実装: コメント行、export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応。
  - OS 環境変数を保護する protected キーセットを導入して .env 上書きを制御。
  - Settings クラスを実装し、J-Quants トークン、kabu API 設定、Slack、DB パス、環境（development/paper_trading/live）、ログレベル検証などのプロパティを提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本的な API 呼び出しユーティリティ _request を実装（JSON デコード、タイムアウト、パラメータ、POST ボディ対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx をリトライ対象。
  - 401 発生時の ID トークン自動リフレッシュ（1 回のみ）とページネーション間で共有するモジュールレベルのトークンキャッシュを実装。
  - fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar のページネーション対応取得関数を実装。
  - DuckDB への冪等保存関数 save_daily_quotes、save_financial_statements、save_market_calendar を実装（INSERT ... ON CONFLICT DO UPDATE）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news に保存する一連処理を実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ削除（utm_ 等）、クエリソート、フラグメント削除。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の軽減）。
    - HTTP リダイレクト時にスキームとホストを検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカルの場合は拒否する _is_private_host を実装し SSRF を防止。
    - URL スキーム検証（http/https のみ）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - テキスト前処理 preprocess_text（URL 除去、空白正規化）。
  - raw_news へのチャンク単位のバルク INSERT（INSERT ... RETURNING を使用）とトランザクション管理を実装（save_raw_news）。
  - news_symbols（記事と銘柄コードの紐付け）を一括保存する機能を実装（_save_news_symbols_bulk / save_news_symbols）。
  - 銘柄コード抽出 extract_stock_codes を実装（4桁数字候補のフィルタリング、既知コードセットと重複除去）。

- DuckDB スキーマ（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル定義を追加。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを追加。
  - features, ai_scores の Feature テーブル、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを追加。
  - テーブル作成順と外部キー依存を考慮した初期化関数 init_schema(db_path) を提供（存在チェック付きで冪等）。
  - 利用頻度を考慮したインデックス群を作成。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、ETL 実行結果（取得数、保存数、品質問題、エラー）を集約。
  - 差分更新ヘルパー（テーブル存在チェック、最終取得日の取得）を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー _adjust_to_trading_day を実装。
  - run_prices_etl（株価差分 ETL）の骨格を実装: 最終取得日からの backfill ロジック、fetch → save 流れを実装（backfill_days デフォルト3日、MIN_DATA_DATE で初回ロードを制御）。

- テスト・モックを想定した設計
  - news_collector._urlopen を差し替え可能にして HTTP 呼び出しをモック可能に設計等、テスト可能性を向上。

### Fixed
- .env パーサーの改善
  - export プレフィックス、クォート内エスケープ、クォートなしでのインラインコメント判定（スペース/タブ直前のみ）など、現実的な .env の記述に対応するためのパースロジックを強化。
- DuckDB への保存で PK 欠損行はスキップし、スキップ数をログ出力するようにしてデータ不整合の状況把握を容易に。

### Security
- RSS パーサーで defusedxml を採用し XML による攻撃ベクトルの軽減。
- RSS フェッチ時の SSRF 対策:
  - リダイレクト先スキーム検査、リダイレクト先ホストのプライベートアドレス判定。
  - 初回 URL および最終 URL の両方でスキームとプライベート判定を実施。
- HTTP レスポンスの最大バイト数制限と gzip 解凍後のサイズチェックを実装しメモリ DoS / Gzip Bomb を軽減。
- 環境変数ローダーで OS 環境変数を保護する設計（protected set）を導入。

### Changed
- （該当なし。初期実装のため変更履歴はなし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

Notes
-----
- 本リリースは動作仕様・設計に関するコード注釈（docstring）を多数含んでおり、実運用に向けた堅牢性（レート制限、再試行、トランザクション、セキュリティ対策）を重視した実装になっています。
- ETL パイプラインやストレージ層は初期実装のため、運用に応じて監視・テスト・性能チューニング（バッチサイズ、並列化、Backoff ポリシー等）が推奨されます。