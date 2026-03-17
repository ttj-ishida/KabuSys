# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」の規約に準拠しています。  

最新の変更は上に記載しています。

## [Unreleased]
- 小さな改善・ドキュメント追記、テストの追加などを予定しています。

---

## [0.1.0] - 2026-03-17

初回リリース (ベータ/アルファ相当)。日本株自動売買プラットフォームの核となるモジュール群の初期実装を追加しました。

### 追加 (Added)
- パッケージのエントリポイント
  - kabusys.__init__ にバージョン情報と公開サブパッケージ一覧を追加。

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（OS 環境変数が優先、.env.local は上書き）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス 等のプロパティを提供。
  - env 値（KABUSYS_ENV）と LOG_LEVEL の値検証を追加（許容値チェックで早期エラー検出）。
  - デフォルトの DB パス（DuckDB/SQLite）を設定、Path.expanduser を利用。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - API レート制御: 固定間隔スロットリングで 120 req/min 制限を順守する RateLimiter を実装。
  - リトライ戦略: 指数バックオフ（最大 3 回）、408/429/5xx を再試行対象とするロジックを追加。
  - 401 受信時は refresh token から id_token を自動リフレッシュして 1 回リトライする仕組みを追加。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - レスポンスの JSON デコード失敗時に詳細を含む RuntimeError を発生させる安全対策。
  - データ保存関数は冪等（ON CONFLICT DO UPDATE）で DuckDB に保存する（raw_prices / raw_financials / market_calendar）。
  - レコードに fetched_at（UTC ISO）を付与し、いつデータを取得したかをトレース可能に。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得・記事抽出・前処理・DB保存の ETL を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 対策: URL スキーム検証 (http/https のみ)、ホストがプライベート IP かどうかの判定、リダイレクト時の事前検査。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査。
  - URL 正規化機能 (_normalize_url): トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソートを実施。
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理: URL 除去、空白正規化を行う preprocess_text。
  - DB 保存:
    - raw_news の挿入はチャンク化して一括 INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された ID を返す。
    - news_symbols（記事と銘柄の紐付け）をチャンク INSERT で一括保存し、挿入件数を正確に取得。
  - 銘柄コード抽出: 正規表現で 4 桁数値を抽出し、known_codes によるフィルタリングで有効なコードのみを返す。

- DuckDB スキーマ・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 4 層に沿ったテーブルを定義する DDL を追加。
  - 主なテーブル: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 各テーブルに適切な型チェック制約と PRIMARY KEY を設定し、データ整合性を確保。
  - 頻出クエリ向けにインデックス（例: code×date、status 等）を作成。
  - init_schema(db_path) でファイルパスの親ディレクトリを自動作成し、全 DDL とインデックスを実行して接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新の概念を実装: DB の最終取得日から backfill_days を考慮して再取得するロジック。
  - 市場カレンダーの先読み（日数指定）や初回ロード用最小日付を定義。
  - ETLResult データクラスを導入して、対象日・取得数・保存数・品質問題・エラー等を集約。
  - 品質チェックモジュール (kabusys.data.quality) と連携する想定（quality.QualityIssue を扱う設計）。
  - run_prices_etl を実装（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes → 結果集計）。※詳細は下記「既知の問題」を参照。

- その他
  - 空のパッケージ初期化ファイルを追加: kabusys.data.__init__, kabusys.data.pipeline, kabusys.execution, kabusys.strategy（将来の拡張用プレースホルダ）。
  - テスト容易性の考慮: news_collector._urlopen をテストでモック可能にする設計、config の自動ロードの無効化フラグなど。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し、XML ベースの攻撃耐性を向上。
- RSS フェッチで SSRF 対策を実装（スキーム検査、プライベートアドレス拒否、リダイレクト検査）。
- 外部との通信でタイムアウトや最大受信サイズを設け、DoS 攻撃やリソース枯渇を軽減。

### 既知の問題 (Known issues / Notes)
- run_prices_etl のソースは取得と保存を行うが、コードスニペットの末尾に戻り値組成の未完/切り取りの痕跡があり（返り値のタプルが途中で終わっているように見える）、最終的な ETL の戻り値フォーマットの確認・整備が必要です。実運用前に unit test による検証を推奨します。
- strategy、execution パッケージは現状プレースホルダのまま。実際の売買ロジック・発注処理は未実装。
- quality モジュールや外部依存（Slack 通知、kabu ステーション連携等）の統合は設計に含まれているが、個別実装・連携テストが必要です。
- DuckDB に依存する SQL 文や RETURNING の挙動はバージョン差により挙動が異なる可能性があるため、利用環境のバージョン確認を推奨します。

---

メジャーリリース/マイナーリリース/パッチのポリシーは Keep a Changelog に準拠します。次回リリースでは strategy/execution の具体化、ETL の完成、品質チェックの本格導入、テスト補強・ドキュメント拡充を予定しています。