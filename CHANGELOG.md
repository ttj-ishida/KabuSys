# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記録します。
このファイルは人間に読みやすく、またリリースノートとして利用できることを目的とします。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)

[Unreleased]
- （現在のリポジトリ状態はバージョン 0.1.0 として最初にリリースされています。以降の変更はここに記載します）

[0.1.0] - 2026-03-18
Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py にてパッケージ名・バージョンを定義（__version__ = "0.1.0"）。
  - 環境設定管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み順序: OS環境変数 > .env.local（上書き） > .env（未設定時のみセット）。
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env 行パーサーで export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理（スペース直前の '#' をコメント扱い）に対応。
    - 環境変数取得用 Settings クラスを提供。J-Quants/J-Quants トークン、kabuステーション API、Slack、DBパス、実行環境（development/paper_trading/live）やログレベル検証などのプロパティを備える。
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - 日足（OHLCV）、財務データ、マーケットカレンダー取得機能を実装。
    - API レート制限を守る固定間隔レートリミッタ（120 req/min）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行）。429 の場合は Retry-After ヘッダ優先。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避）。
    - ページネーション対応でモジュールレベルのトークンキャッシュを共有。
    - データ取得時に fetched_at を UTC タイムスタンプで記録（Look-ahead bias 対策）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等化（ON CONFLICT DO UPDATE）されている。
    - 数値変換ユーティリティ（_to_float, _to_int）で安全に変換。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードから記事を収集して raw_news に保存する処理を実装（DataPlatform.md に準拠）。
    - セキュリティ・堅牢化:
      - defusedxml を使用して XML Bomb 等に対処。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先の事前検証、ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否。
      - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）を設け、Gzip 解凍後もサイズ検査（Gzip bomb 対策）。
      - User-Agent と Accept-Encoding ヘッダの設定。
    - 記事ID は正規化した URL の SHA-256（先頭32文字）で生成し冪等性を保証（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - テキスト前処理（URL 除去・空白正規化）と公開日パース（RFC2822→UTC変換）。パース失敗時は代替で現在時刻を使用（raw_news.datetime は NOT NULL）。
    - DuckDB への保存はチャンク化して一括 INSERT、トランザクションで行い INSERT ... RETURNING を使って実際に挿入されたIDを返す。news_symbols の紐付けも重複排除＋チャンク挿入で効率化。
    - 銘柄コード抽出ロジック（4桁数字候補を known_codes と照合して重複除去）。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を定義。
  - DuckDB スキーマ定義 (src/kabusys/data/schema.py)
    - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を追加。
    - raw_prices / raw_financials / raw_news / raw_executions、processed 層（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）、features / ai_scores、および execution 層（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を含む。
    - 各テーブルのチェック制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）や適切な型を設定。
    - 代表的クエリに合わせたインデックス群を作成。
    - init_schema(db_path) でディレクトリ作成→全DDL適用→接続を返すユーティリティ、get_connection() で接続取得。
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分更新型 ETL を実装（最終取得日を確認し未取得範囲のみを API から取得）。
    - backfill_days により最終取得日の数日前から再取得して API の後出し修正に対応（デフォルト 3 日）。
    - 市場カレンダーの先読み（lookahead 値）や初回ロード用の最小日付定義。
    - 品質チェック（quality モジュール利用を想定）を組み込み、致命的な品質問題の有無判定機能を ETLResult に保持（品質問題は収集を継続）。
    - ETLResult dataclass を導入し、fetch/save カウント、品質問題リスト、エラーリストを集約。to_dict() でシリアライズ可能。
    - DB テーブル存在チェックや最大日付取得ヘルパーを提供。
    - run_prices_etl() など個別 ETL ジョブの雛形を追加（差分計算と jquants_client の fetch/save 呼び出しを実装）。  

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集における SSRF・XML 攻撃・メモリ DoS（巨大レスポンス/Gzip bomb）対策を実装。
- .env 読み込み時に OS 環境変数を保護する protected セットを導入し、.env.local の上書き制御を明示。

注記 / マイグレーション
- 初回リリースでスキーマ定義が導入されています。既存データベースがある場合は init_schema() を使う前にバックアップを推奨します。
- .env 自動ロードはプロジェクトルート検出に依存します。パッケージ配布後に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のアクセストークンは Settings.jquants_refresh_token 経由で提供してください（未設定時は ValueError を発生させます）。
- news_collector の fetch_rss / save_raw_news の挙動は、外部ネットワークや DNS の解決状態に依存します。テスト時は _urlopen をモックして外部接続を遮断してください。

--- 

（今後のリリースでは機能追加・バグ修正・API 互換性の変更点をここに追記します）