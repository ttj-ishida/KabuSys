KEEP A CHANGELOG
すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

Unreleased
---------
- （無し）

[0.1.0] - 2026-03-17
-------------------
Added
- パッケージ初期リリース: kabusys v0.1.0 を導入。
  - パッケージ公開情報（src/kabusys/__init__.py）に __version__ と __all__ を定義。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の export 形式・コメント・クォート・エスケープ処理に対応するパーサを実装。
  - 必須環境変数取得ヘルパー _require と、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_ENV (development, paper_trading, live) と LOG_LEVEL のバリデーションを実装。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得 API を実装（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔レートリミッタを導入。
  - リトライ戦略（指数バックオフ, 最大3回）を実装。408/429/5xx をリトライ対象に設定。
  - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
  - 取得データに fetched_at を UTC で付与し、Look-ahead bias を防止。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等化を実現。
  - 型安全な数値変換ユーティリティ（_to_float / _to_int）を実装。
- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード取得（fetch_rss）と記事前処理・正規化・ID生成・保存ロジックを実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
  - XML パーサに defusedxml を利用して XML-Bomb 等の攻撃対策を実装。
  - SSRF 対策を多数実装:
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストかをチェックして拒否。
    - リダイレクト時にもスキームとプライベートアドレス検証を行うカスタム RedirectHandler を組み込み。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を導入し、gzip 解凍後のサイズも検証（Gzip bomb 対策）。
  - RSS の pubDate を UTC に正規化して扱う処理を実装。
  - raw_news の一括挿入（チャンク・トランザクション・INSERT ... RETURNING）と news_symbols（銘柄紐付け）保存処理を実装。重複除去とトランザクション制御あり。
  - テキスト前処理（URL 除去、空白正規化）と本文からの銘柄コード抽出ユーティリティを実装（4桁コード、既知コードセットフィルタ）。
  - デフォルトの RSS ソースに Yahoo Finance のカテゴリーフィードを設定。
- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution 層を想定したテーブル群を DDL で定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに適切な主キー・外部キー・CHECK 制約を付与してデータ整合性を強化。
  - 頻出クエリ用のインデックス定義を追加。
  - init_schema(db_path) によりフォルダ作成・DDL 実行・インデックス作成を行い、DuckDB 接続を返すユーティリティを提供。get_connection() で既存 DB へ接続可能。
- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新ロジックを実装: DB の最終取得日を元に差分（およびデフォルト backfill_days=3 による再取得範囲）を自動算出。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS=90）やデータ開始日の定義（_MIN_DATA_DATE）を導入。
  - ETL 実行結果を表す ETLResult データクラスを導入（品質チェック結果・エラー一覧・集計を含む）。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ヘルパーを実装。
  - run_prices_etl を実装（fetch + save の呼び出し、取得数/保存数の返却）。fetch/save は jquants_client の関数を利用。
  - 品質チェックモジュール（quality）との連携を想定した設計（非 Fail-Fast、問題の収集と報告を行う方針）。
- パッケージ構造の雛形を追加（execution, strategy, data パッケージインデックスファイル）。

Security
- ニュース収集でのセキュリティ強化:
  - defusedxml による XML パース防御。
  - SSRF 対策（URL スキーマ検証、プライベートIP検査、リダイレクト時の事前検証）。
  - 応答サイズ上限・gzip 解凍後チェックによるメモリ DoS / Gzip bomb 対策。
- jquants_client の HTTP 例外処理でリトライ・Backoff を導入し、過負荷や一時的なネットワーク問題に耐性を持たせた。

Documentation / Usability
- config.Settings に docstring と利用例を追加。設定値取得は properties 経由に統一。
- jquants_client と news_collector のログ出力を充実させ、操作性と監査性を向上。

Fixed
- J-Quants へのリクエスト実装で以下を改善:
  - JSON デコード失敗時の明示的エラー報告。
  - 401 でのトークン自動リフレッシュを 1 回に制限して無限再帰を防止。
  - 429 の Retry-After ヘッダ優先処理を実装。

Notes / Migration
- データベース初期化は init_schema(db_path) を実行してください。":memory:" を渡すとインメモリ DB を使用できます。
- .env 自動読み込みはプロジェクトルート検出に依存します。配布後またはテスト時に自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector の extract_stock_codes は known_codes を利用する設計です。既存の銘柄セットを渡すことでノイズを減らせます。
- pipeline モジュールは品質チェックモジュール（quality）に依存した設計になっているため、品質チェックの実装/接続を行ってから本番運用を開始してください。

Deprecated
- なし

Removed
- なし

Acknowledgements / Known limitations
- quality モジュールの実装はこのコードセットからは確認できません（pipeline が参照）。品質チェックの具備は別途必要です。
- Slack / kabu API 実行周りの実装（実際の発注ロジック）は本リリースでは含まれておらず、execution/strategy パッケージは雛形のみです。発注・モニタリング機能は今後のリリースで追加予定。

（以上）