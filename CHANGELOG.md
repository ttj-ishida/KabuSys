# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-17
初回リリース（初期実装）。日本株自動売買システム KabuSys のコア機能群を実装しました。

### 追加
- パッケージのエントリポイントを追加
  - pkg: kabusys、バージョン情報を src/kabusys/__init__.py に定義（__version__ = "0.1.0"）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
  - export プレフィックスやクォート値、インラインコメント等に対応した .env パーサ実装。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テストでの差し替えを容易化。
  - OS 環境変数を保護する protected ロジック（.env.local は override=True だが OS 変数は上書きしない）。
  - アプリ設定ラッパー Settings を実装（J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定等のプロパティ）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制限を守る固定間隔スロットリング実装（120 req/min の RateLimiter）。
  - 再試行戦略（指数バックオフ、最大 3 回、408/429/5xx に対応）。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時はリフレッシュトークンから id_token を自動取得して 1 回だけ再試行。
  - API 呼び出しの JSON デコードエラーハンドリングと説明的な例外。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装（raw_prices / raw_financials / market_calendar）。
  - 取得時刻を UTC 形式の fetched_at に保存し、Look-ahead Bias のトレーサビリティを確保。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、入力の堅牢性を向上。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する一連処理を実装。
  - 安全性を重視した設計:
    - defusedxml を利用した XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検査、リダイレクト時の検査ハンドラ実装（_SSRFBlockRedirectHandler）。
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成し冪等性を担保（トラッキングパラメータ除去、クエリソート等で正規化）。
  - テキスト前処理（URL 除去、空白正規化）関数と、記事内からの銘柄コード抽出（4桁数字フィルタリング、既知銘柄セットによるフィルタ）を実装。
  - DB 保存はチャンク化して一括 INSERT（INSERT ... RETURNING を用いて実際に追加された ID/件数を返却）、トランザクション管理を実装。
- スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DuckDB 用の包括的スキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - 各種テーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設計し、データ整合性を強化。
  - 頻出クエリに備えてインデックスを作成する DDL を用意。
  - init_schema(db_path) によりディレクトリ作成→全DDL・インデックス適用→接続を返す機能を実装。get_connection で既存 DB への接続を取得可能。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新方式の ETL 実装（差分開始日の自動算出、backfill 日数オプションで後出し修正を吸収）。
  - run_prices_etl 等の個別 ETL ジョブ実装を開始（取得→保存→ログ記録）。
  - ETL 結果を表す ETLResult データクラスを追加（品質問題、エラーの集約、辞書化ユーティリティ）。
  - 市場カレンダーを考慮した営業日調整、テーブル存在チェック、最大日付取得ユーティリティを提供。
- その他
  - モジュールに型注釈を導入（Python 3.10+ 型ヒント利用）。
  - logger を各モジュールに配置して情報/警告/エラーの記録を統一。
  - data パッケージ内で将来の拡張用の __init__.py を用意。
  - strategy と execution パッケージの初期化ファイルを配置（プレースホルダ）。

### 変更
- （初期リリースのため該当なし）コード設計上の注記として以下を明記:
  - DB 操作は冪等性を重視（ON CONFLICT 句、INSERT ... RETURNING、チャンク化）。
  - API 呼び出しはスロットリング + リトライ + トークン自動リフレッシュで堅牢化。
  - ニュース収集はセキュリティ（SSRF, XML Bomb, Gzip bomb）に強い実装。

### 修正
- （初回実装）多くのコーナーケース（.env の引用符やコメント処理、RSS の content:encoded 優先、guid の代替利用など）に対応するため細かなハンドリングを実装。

### セキュリティ
- RSS パーサで defusedxml を使用して XML 攻撃を軽減。
- HTTP リダイレクト時にスキーム/ホストを検査し、内部ネットワークや非 http/https スキームへのアクセスを防止。
- .env の自動読み込み時に OS 環境変数を上書きしない保護機能を実装し、意図せぬ資格情報上書きを防止。

### 既知の制限・今後の課題
- strategy および execution パッケージはプレースホルダ（未実装のロジックあり）。発注実行ロジックの実装が必要。
- quality モジュール（品質チェック）は pipeline から参照される想定だが、完全実装状況に依存する（存在が仮定されている）。
- 単体テストや統合テストのカバレッジは今後拡充が必要。テスト用フック（KABUSYS_DISABLE_AUTO_ENV_LOAD、_urlopen のモック可能性等）は考慮済み。
- 一部の DB 型変換や外部 API エラーケースに関して、追加の監視・アラート機構が望ましい。

---

訳注: 本 CHANGELOG は現在のコードベース（src/ 配下の実装内容）から推測して作成した初期リリース向けの変更履歴です。実際のコミット履歴や公開リリースノートがある場合はそれに合わせて調整してください。