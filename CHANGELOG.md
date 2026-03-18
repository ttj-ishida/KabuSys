# Changelog

すべての変更は Keep a Changelog の原則に従って記載しています。  
このリポジトリはセマンティックバージョニングに従います。

最新リリース
- バージョン: 0.1.0
- リリース日: 2026-03-18

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ基盤
  - パッケージ名 kabusys を追加。パッケージのバージョンは `__version__ = "0.1.0"`。
  - 公開モジュール: data, strategy, execution, monitoring（strategy/execution は初期プレースホルダ）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動読み込み機能を実装。
    - プロジェクトルート判定は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD 非依存）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用）。
  - .env パーサを実装:
    - `export KEY=val` 形式対応、クォート文字列内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを考慮。
  - 必須設定を取得する `Settings` クラスを提供:
    - J-Quants、kabu API、Slack、データベースパスなどのプロパティ (`jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `slack_channel_id`, `duckdb_path`, `sqlite_path` など)。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（サポートされる値セットを強制）。
    - `is_live`, `is_paper`, `is_dev` の簡易判定プロパティ。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - 設計上の特徴:
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守（モジュール内 RateLimiter 実装）。
    - リトライ: 指数バックオフを用いたリトライ（最大 3 回）。リトライ対象は 408/429 と 5xx。429 の場合は Retry-After を優先。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - 取得時刻（fetched_at）を UTC ISO フォーマットで記録し、Look-ahead バイアス対策。
    - DuckDB へ保存する際は冪等性を担保するため ON CONFLICT DO UPDATE を使用（save_daily_quotes / save_financial_statements / save_market_calendar）。
  - ユーティリティ: 型変換関数 `_to_float`, `_to_int`（不正値や空値を None にするロジックを含む）。
  - 認証ヘルパー `get_id_token` を実装（refresh token から idToken を取得）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集して raw_news テーブルに保存するモジュール。
  - 設計上の特徴（セキュリティ・堅牢性重視）:
    - defusedxml を利用して XML Bomb 等の攻撃を防御。
    - SSRF 対策:
      - 初期 URL とリダイレクト先のスキーム検証（http/https のみ許可）。
      - リダイレクト時にホストがプライベート / ループバック / リンクローカルであればアクセスを拒否（カスタム RedirectHandler 実装）。
      - DNS で解決した IP アドレスの判定も実施。DNS 解決失敗時は安全側で通過させる設計。
    - 受信サイズ制限: MAX_RESPONSE_BYTES = 10MB（Content-Length と実際の読み込み量の両方でチェック）。gzip 解凍後のサイズ検証も行う（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ（utm_* 等）の削除。
    - 記事 ID は正規化後 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性確保）。
    - テキスト前処理: URL 除去と空白正規化。
    - DB 保存:
      - raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク毎に実行、INSERT ... RETURNING で新規挿入した記事 ID を正確に返す。トランザクションでまとめてコミット。
      - news_symbols: 記事と銘柄コードの紐付けを INSERT ... RETURNING で保存し、実際に挿入された件数を返す。
    - 銘柄抽出: 4 桁数字パターン（日本株）から known_codes に含まれるコードのみを抽出する `extract_stock_codes` を実装。
    - 統合ジョブ `run_news_collection` を実装（各ソースは独立してエラーハンドリング、known_codes に基づく紐付け処理を一括で行う）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Data Platform 設計に基づき、Raw / Processed / Feature / Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに対する型制約・チェック制約（CHECK）や主キー・外部キーを設定。
  - よく使うクエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - 初期化関数 `init_schema(db_path)` を提供（ファイルパス親ディレクトリ自動作成、DDL を冪等に実行して接続を返す）。
  - 既存 DB への接続を返す `get_connection(db_path)` を提供（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL のためのユーティリティと差分更新ジョブの基盤を実装。
  - 設計上の特徴:
    - 差分更新ロジック: 最終取得日からの差分のみ取得、デフォルトのバックフィル日数は 3 日（後出し修正を吸収するため）。
    - 市場カレンダーの先読み（lookahead）と最小データ日付（2017-01-01）。
    - 品質チェック用の枠組み（quality モジュールとの連携を想定）。ETLResult に品質問題を格納し、致命的品質エラーがあっても可能な限り処理を継続する設計。
  - `ETLResult` データクラスを追加（処理結果、品質問題、エラーの要約を保持。辞書化メソッド含む）。
  - DB ヘルパー: テーブル存在チェック、テーブルの最大日付取得、営業日調整ヘルパー（market_calendar に基づく過去方向調整）。
  - 差分 ETL の実装例: `run_prices_etl`（target_date と date_from/backfill の扱い、jquants_client の fetch/save を呼び出し）。  

### 変更 (Changed)
- 初期リリースのため該当なし（新規実装リリース）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- news_collector における SSRF 対策、defusedxml 利用、受信サイズチェック（Gzip 解凍後も含む）など、外部入力に対する堅牢性を強化。
- .env パースにおける引用符内のエスケープ処理を実装し、不正な設定解釈のリスクを低減。

### 既知の問題 / 注意点 (Known issues / Notes)
- strategy/ execution/ monitoring モジュールはエントリポイント（__all__）に含まれているものの、実装は空のパッケージ/モジュールとなっており、機能は未実装です。
- pipeline.run_prices_etl の末尾が実装途中（スニペットが途切れている）であり、リリース時点ではこの関数が未完または切断された戻り値になっている可能性があります。実行時の動作確認と補完実装が必要です。
- ネットワーク呼び出し（J-Quants API、RSS フィード）は外部依存のため、環境変数やネットワーク状態に応じたエラーが発生します。自動テストでは id_token 注入やモック化を推奨します。
- DuckDB による ON CONFLICT / RETURNING 等の SQL を利用しているため、環境の DuckDB バージョンや Python バインディングとの互換性に注意してください。

### マイグレーション / 移行メモ (Upgrade notes)
- 初回導入時は `init_schema()` を必ず実行して DuckDB のスキーマを作成してください。
- 環境設定は .env.example を元に `.env` をプロジェクトルートに作成すると自動読み込みされます。CI・テストで自動ロードを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- J-Quants のアクセストークンは `JQUANTS_REFRESH_TOKEN` 環境変数で供給する必要があります。

### 開発者 / 貢献 (Contributors)
- 初期実装 — 機能の骨格および主要なデータ取得/保存ロジック、RSS 収集の堅牢化に注力。

---

今後のリリース予定（例）
- strategy / execution の具体実装（シグナル生成、発注実行/約定処理、ポジション管理）
- pipeline の品質検査モジュール（quality）の実装と ETL の完全統合
- テストカバレッジ強化・CI ワークフロー整備
- ドキュメント（DataPlatform.md, API 利用例、運用手順）の充実

もし特定のモジュール（例: news_collector の動作確認手順、DuckDB スキーマの詳細、ETL の実行方法）について CHANGELOG に追記や補足を希望される場合は、その旨を教えてください。追加で項目を整備します。