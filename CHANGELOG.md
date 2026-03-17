# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

文書はコードベースから推測して作成しています。実装や履歴の詳細はソースコード（src/kabusys）を参照してください。

## [Unreleased]

- （現時点の開発中の変更や予定されている改善点をここに記載）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装・公開。

### 追加 (Added)

- パッケージ構成
  - 主要パッケージ公開: kabusys (サブモジュール: data, strategy, execution, monitoring)
  - バージョン: 0.1.0 を __init__.py に定義

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）
  - .env パーサの実装
    - export 宣言、クォート文字列、インラインコメント、エスケープ対応
  - Settings クラスによる型付きアクセス
    - J-Quants / kabuステーション / Slack / DB パス 等の設定プロパティ
    - env 値や LOG_LEVEL のバリデーション（有効値チェック）
    - パスは Path 型で返すユーティリティ（expanduser 対応）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ実装（JSON パース、エラーハンドリング）
  - レート制御: 固定間隔スロットリングによる 120 req/min の遵守（内部 RateLimiter）
  - リトライロジック: 指数バックオフ、最大 3 回（408/429/5xx 等を再試行）
  - 認証トークン（id_token）管理
    - リフレッシュトークンからの id_token 取得
    - 401 受信時に自動でトークンをリフレッシュして 1 回リトライ（無限再帰対策）
    - モジュールレベルのトークンキャッシュを共有（ページネーション対応）
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期 BS/PL 等）
    - fetch_market_calendar（JPX カレンダー）
    - 取得時にログでフェッチ件数を記録
  - DuckDB への冪等保存関数
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を用いた冪等性確保
    - PK 欠損行のスキップと警告ログ

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news に保存する完全な収集フローを実装
    - デフォルトソース: Yahoo Finance のビジネスカテゴリ RSS を含む DEFAULT_RSS_SOURCES
    - fetch_rss による RSS 取得とパース
    - preprocess_text による URL 除去・空白正規化
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証
    - defusedxml を使用して XML Bomb 等の脅威に対応
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策
    - gzip 圧縮対応と gzip 解凍後のサイズ再チェック（Gzip bomb 対策）
    - SSRF 対策
      - URL スキーム検証（http/https のみ）
      - リダイレクト時のスキーム/ホスト検証用カスタム RedirectHandler
      - ホストがプライベート/ループバック/リンクローカル/IP の場合は拒否
    - DB 保存はチャンク化してトランザクションで実行、INSERT ... RETURNING を利用して実際に挿入された ID を返す
  - 銘柄コード抽出
    - 正規表現により 4 桁数字を抽出し、known_codes に基づくフィルタリング
    - extract_stock_codes で重複排除して返却
  - run_news_collection による統合収集ジョブ
    - 各ソースは独立してエラーハンドリング（1 ソース失敗でも他ソース継続）
    - 新規記事に対して銘柄紐付けを一括で保存（重複排除・チャンク挿入）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution レイヤーのテーブル定義を実装
  - 主要テーブル（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）を含む DDL を定義
  - 外部キーや CHECK 制約を含めた型安全なスキーマ
  - 利用頻度を想定したインデックス定義
  - init_schema(db_path) で親ディレクトリ自動作成、DDL を一括実行して接続を返す（冪等）
  - get_connection(db_path) による既存 DB 接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新方式の ETL をサポート
    - DB の最終取得日を基に差分（前日分など）を自動算出して取得
    - backfill_days による後出し修正吸収（デフォルト 3 日）
    - 市場カレンダーの先読み（デフォルト 90 日）
  - ETLResult dataclass による実行結果の記録（品質問題やエラーの一覧を保持）
  - テーブル存在チェック、最大日付取得などのユーティリティ実装
  - run_prices_etl などのジョブ（差分取得 → 保存 → ログ）

### セキュリティ (Security)

- RSS パーサに defusedxml を採用し XML 攻撃を軽減
- SSRF 対策を複数実装（スキーム検証、リダイレクト時の検査、プライベート IP 検査）
- 外部リソース読み込みに対する応答サイズ上限を設け、Gzip 解凍後も再チェック

### パフォーマンス / 信頼性 (Performance / Reliability)

- API 呼び出しにレートリミッタとリトライ（指数バックオフ、Retry-After 優先）を実装
- トークン管理のキャッシュ化によりページネーション間での再取得を最小化
- DB 書込みをチャンク/トランザクション化、INSERT ... RETURNING により実挿入数を正確に把握
- DuckDB スキーマにインデックスを追加し検索パターンに備える

### ドキュメント・注記 (Documentation / Notes)

- 各モジュールに詳細な docstring を記載（設計方針、処理フロー、セキュリティ注意点、戻り値・例外の説明等）
- テストや差し替えを容易にするフックを用意（例: news_collector._urlopen をテストでモック可能）
- settings で必須環境変数が未設定の場合は明確なエラーメッセージを出す（.env.example 参照を促す）

---

開発者向け注意:
- schema.init_schema() を使って最初に DB を初期化してください。既存 DB に対しては get_connection() を使用します。
- 自動 .env ロードが不要な環境（CI テスト等）では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

（以降のバージョンでは strategy / execution / monitoring の具体的なアルゴリズムや実装の追加、品質チェックモジュールの詳細実装、細かなエラー処理改善などを行う予定です。）