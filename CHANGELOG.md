# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」に準拠しています。

全てのバージョンはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システムのコアモジュール群を実装しました。以下はコードベースから推測してまとめた主要な追加・実装内容です。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージを導入。サブパッケージとして data, strategy, execution, monitoring を公開（strategy と execution は初期プレースホルダ）。
  - パッケージバージョンは `0.1.0` に設定。

- 環境変数／設定管理 (`kabusys.config`)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み優先度は OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env のパースはシェル形式（export プレフィックス、シングル／ダブルクォート、コメント扱い）に対応。
  - Settings クラスを提供し、以下の設定をプロパティ経由で取得可能:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）等
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。is_live / is_paper / is_dev の補助メソッドあり。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリングにより 120 req/min を遵守する `_RateLimiter` を実装。
  - リトライ戦略: 指数バックオフで最大 3 回リトライ、HTTP 408/429/5xx を再試行対象とする実装。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュを実装。
  - API 呼び出し共通関数 `_request` により JSON デコード・例外処理を整理。
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を利用）。
  - 型変換ユーティリティ `_to_float` / `_to_int` を追加し、入力データの堅牢な取り扱いを実現。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事収集し DuckDB の raw_news へ保存する機能。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - SSRF 防止: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定とリダイレクト検査（カスタム RedirectHandler）、受信サイズ上限チェック（最大 10MB）を実装。
    - gzip 解凍時のサイズ検査（Gzip bomb 対策）。
  - 記事 ID は正規化した URL の SHA-256（先頭 32 文字）で生成し冪等性を担保（utm_* 等のトラッキングパラメータを除去してから正規化）。
  - テキスト前処理（URL 除去・空白正規化）と RSS pubDate の安全なパースを実装。
  - DB 保存はトランザクションでまとめて行い、INSERT ... RETURNING を用いて実際に挿入された件数／ID を正確に取得する。
  - 銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタ）と、一括で news_symbols に保存する仕組みを実装。

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - Data Platform 設計に基づくスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義し、データ整合性を担保。
  - 頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) でディレクトリ作成・DDL 実行・接続を返す関数を提供。get_connection() で既存 DB へ接続可能。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計に沿った差分更新ロジックの基礎を実装。
  - ETLResult dataclass を導入し、取得件数・保存件数・品質問題・エラー等を集約して返却可能。
  - DB 上の最終取得日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 市場カレンダーがある場合に営業日に調整するヘルパー `_adjust_to_trading_day` を実装。
  - run_prices_etl の雛形を実装（差分算出、バックフィル、fetch/save の呼び出し）。（詳細な品質チェックや他ジョブとの統合は別実装想定）

### セキュリティ (Security)
- ニュース収集に対して SSRF・XML 注入・メモリ DoS（大きなレスポンス）等への対策を導入。
- .env 読み込みは OS 環境変数を保護する設計（protected set を使って上書きを制御）。

### 改善 (Improvements)
- API クライアントと ETL が冪等性を保つよう設計（DuckDB 側で ON CONFLICT による更新を行うため再実行可能）。
- エラー・リトライ・ログ出力を詳細化して運用時のトラブルシュートしやすく設計。

### 既知の制限 / 今後の課題 (Known issues / TODOs)
- strategy / execution / monitoring はパッケージプレースホルダとして存在。戦略実装や発注ロジックはこれからの実装が想定される。
- pipeline.run_prices_etl などは骨格実装（品質チェックや全体の ETL オーケストレーションの追加実装が必要）。
- 単体テストや統合テスト用のモック・テストケースの整備が必要（例: _urlopen をモックして RSS テストを実施）。

---

この CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時は運用上の決定や変更履歴の差分を反映してください。