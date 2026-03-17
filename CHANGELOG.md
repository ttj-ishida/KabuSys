CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

リンク: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現在のスナップショットでは未リリースの変更はありません）

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコア実装を追加。
- パッケージ構成
  - kabusys.config: 環境変数/設定の自動読み込みと管理機能を実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env の行パース時に export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
    - Settings クラスを公開し、J-Quants・kabu API・Slack・DB パス・環境（development/paper_trading/live）・ログレベル等のプロパティを提供。値検証（許容値チェック）を実装。
- データ取得 / 保存（kabusys.data）
  - jquants_client:
    - J-Quants API クライアントを実装。株価日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダーの取得に対応。
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等性を意識した DuckDB への保存関数（ON CONFLICT DO UPDATE）。
    - ページネーション対応、401 時のトークン自動リフレッシュ（1回のみ）、ネットワーク/HTTP エラーに対するリトライ（指数バックオフ、最大3回、429 の Retry-After 優先）を実装。
    - データ取得時の fetched_at を UTC で記録して Look-ahead Bias を防止。
    - 型変換ユーティリティ（_to_float/_to_int）を実装。
  - news_collector:
    - RSS フィードからニュースを収集して raw_news に保存するモジュールを実装。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）、正規化 URL の SHA-256（先頭32文字）による記事ID生成。
    - defusedxml を使用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - リダイレクト時にスキームとホストを検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないかを検査（IP 直接判定および DNS 解決の A/AAAA レコード確認）。
      - 許可されないスキームやプライベートホストは拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）や gzip 解凍後のサイズチェックを実装し、メモリ DoS / Gzip bomb を防止。
    - 前処理: URL 除去・空白正規化を行う preprocess_text。
    - DB 保存: チャンク分割によるバルク INSERT、トランザクションでのまとめ挿入、INSERT ... RETURNING を利用して実際に挿入された記事IDやレコード数を返却。ON CONFLICT で重複をスキップ。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes でフィルタ。news_symbols テーブルへの一括挿入サポート。
  - schema:
    - DuckDB 用スキーマ定義と初期化関数を実装（init_schema/get_connection）。
    - Raw / Processed / Feature / Execution の各レイヤー向けテーブル定義を網羅的に追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 主要クエリ向けインデックスを追加（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
    - スキーマ初期化は冪等（CREATE IF NOT EXISTS）で実装。
- data.pipeline:
  - ETL パイプライン基盤を実装。
    - ETLResult データクラスで ETL 結果（取得数／保存数／品質検査結果／エラー等）を集約・辞書化できる機能を提供。
    - テーブル存在チェック・最大日付取得ユーティリティ（_table_exists/_get_max_date）。
    - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
    - 差分更新のためのヘルパー（get_last_price_date 等）。
    - run_prices_etl: 差分更新（最終取得日からの backfill を考慮）→ J-Quants から取得 → DuckDB に保存、というフローを実装（差分更新ロジック、backfill_days デフォルト3日）。
  - デザイン方針: 差分更新単位は営業日、backfill により後出し修正を吸収、品質チェックは Fail-Fast とせず呼び出し元で判断可能。

Security
- RSS XML のパースに defusedxml を採用し、XML 関連の攻撃（XML Bomb 等）に対処。
- RSS フェッチでの SSRF 対策を実施（スキームチェック・プライベートアドレス検出・リダイレクト検査）。
- .env 読み込みでは OS 環境変数を保護する protected ロジックを導入。

Performance
- J-Quants API 呼び出しのレート制御（120 req/min）を実装。
- news_collector のバルク挿入でチャンク化を採用し、トランザクションをまとめてオーバーヘッドを低減。

Reliability
- API 再試行（指数バックオフ、Retry-After 優先、401 のトークンリフレッシュ）による堅牢性向上。
- DuckDB への保存は冪等（ON CONFLICT）で実装され、重複や再実行に耐える設計。
- DB 操作はトランザクションで保護し、失敗時はロールバックして例外を再送出。

Notes / Known limitations
- run_prices_etl 等の ETL 関数は差分更新の主要ロジックを実装していますが、外部の品質チェックモジュール（kabusys.data.quality）との連携部分はこのスナップショットから想定される設計に基づく実装が前提です。
- 単体テストや統合テストのために、news_collector._urlopen のモック置換を利用する設計になっています。運用時はネットワーク環境・認証情報（環境変数）の設定が必須です。

貢献・報告
- 不具合や改善提案は Issue を立ててください。開発ガイドラインや API 仕様書（DataPlatform.md, DataSchema.md 等）に沿った追加/修正を歓迎します。