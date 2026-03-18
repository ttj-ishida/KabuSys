# Changelog

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングを使用します。
このファイルは日本語で記載しています。

注: ソースコードから推測可能な実装内容・設計意図に基づき記載しています（ドキュメント・コメント・命名からの推測）。

## [0.1.0] - 2026-03-18

初回公開リリース（ベース実装）。日本株自動売買システムのコアモジュール群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのベースを追加。バージョンは 0.1.0。公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を自動読み込みする機能を追加。
  - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準に探索し、自動ロードを行う）。
  - .env/.env.local を優先度付きで読み込む（OS 環境変数を保護する protected 機構を搭載）。
  - .env 行パーサ実装（コメント行、export プレフィックス、クォート内エスケープ、インラインコメントの取り扱いに対応）。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化が可能。
  - 環境（development / paper_trading / live）やログレベルの検証ロジックを実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants からのデータ取得用クライアントを実装。
  - レート制限（120 req/min）を遵守する固定間隔スロットリング実装（_RateLimiter）。
  - HTTP 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 受信時のリフレッシュトークンによる自動 ID トークン更新（1 回のみの保証）を実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements を実装。
  - fetch_market_calendar を実装（祝日・半日・SQ 取得）。
  - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
  - JSON デコードエラーや HTTP タイムアウト等のエラーハンドリングとログ出力を備える。
  - 型変換ユーティリティ _to_float / _to_int を実装し、不正値に対して安全に None を返す処理を提供。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を安全に収集・前処理・保存する完全なモジュールを追加。
  - セキュリティ対策:
    - defusedxml ベースの XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時にスキームとホスト/IP を検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）と、hosts がプライベートアドレスか判定するロジック(_is_private_host)。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - フィード処理:
    - URL 正規化およびトラッキングパラメータ（utm_* 等）の除去。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL 削除、空白正規化）。
    - pubDate の安全なパース（UTC 正規化、パース失敗時は現在時刻にフォールバック）。
  - DB 保存:
    - raw_news へのチャンク単位のバルク INSERT（ON CONFLICT DO NOTHING）と INSERT ... RETURNING を使った新規追加ID取得。
    - news_symbols（記事と銘柄コードの紐付け）をバルクで保存する機能（ON CONFLICT 排除、トランザクションにより安全化）。
  - 銘柄コード抽出ユーティリティ（4桁数字から known_codes と照合して抽出）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の包括的スキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions の定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance などのテーブル定義。
  - 各種制約（主キー、外部キー、CHECK）を付与してデータ整合性を保護。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) によりディレクトリ作成 → 全 DDL とインデックスを実行して初期化するユーティリティを実装。
  - get_connection(db_path) を提供（スキーマ初期化を行わない接続取得）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 処理の基本設計（差分更新、backfill、品質チェック呼び出し）に基づくモジュールを実装。
  - ETLResult dataclass を導入し、取得件数・保存件数・品質問題・エラー等を集約して返却可能に。
  - 差分更新ヘルパー（テーブル存在確認、最大日付取得、営業日調整）を実装。
  - run_prices_etl のベース実装（差分算出、J-Quants からの取得、DuckDB への保存）を追加。
  - 市場カレンダーの先読みやデフォルトバックフィル日数等の設定を導入。

### 変更 (Changed)
- N/A（初回リリースのため履歴変更なし）

### 修正 (Fixed)
- N/A（初回リリース）

### セキュリティ (Security)
- RSS パーサーに defusedxml を採用し、XML 関連の脆弱性に対処。
- SSRF 対策を導入（リダイレクト時と最終 URL の検査、プライベートIPチェック）。
- ネットワークから受信するサイズを制限し、メモリ DoS を軽減。

### 既知の制限 / 注意点 (Known issues / Notes)
- strategy / execution / monitoring パッケージは名前空間として存在するが、詳細実装はこのリリースでは未実装（プレースホルダ）。
- ETL パイプラインは品質チェックモジュール(kabusys.data.quality)との連携を前提としているが、その実装はここから読み取れる範囲では未提示。品質チェックが未実装の場合でも ETL は継続する設計。
- J-Quants API のリトライ・レート制御は実装済みだが、実動作は実際の API レートや応答ヘッダ（Retry-After など）に依存するため、本番運用前に実負荷下での検証を推奨。
- news_collector の DNS 解決失敗時は安全側で通過させる実装としている（セーフフォールバック）。ネットワーク環境によって挙動が異なる場合あり。

### 互換性 (Compatibility)
- 破壊的変更はありません（初回リリース）。

---

今後の予定（推測）
- strategy / execution / monitoring の具体実装（シグナル生成・注文送信・監視アラート等）。
- 品質チェックモジュールの実装強化と ETL への統合。
- 単体テスト／統合テストの充実（外部 API のモック化を含む）。
- ドキュメント（DataPlatform.md, API 利用手順, 運用手順）の拡充。