# KabuSys

日本株自動売買プラットフォームのコアライブラリ。データ収集（J-Quants, RSS）、ETLパイプライン、DuckDBベースのスキーマ、データ品質チェック、監査ログ等を提供します。戦略・実行・監視の各レイヤー用の基盤を備え、冪等性・トレーサビリティ・セキュリティ（SSRF対策など）を考慮して設計されています。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得
  - レート制限（120 req/min）を守るスロットリング
  - リトライ（指数バックオフ）、401時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- RSSニュース収集
  - RSSフィードの取得、前処理（URL除去・空白正規化）
  - URL正規化→SHA-256先頭32文字で記事IDを生成して冪等性を担保
  - SSRF対策（スキームチェック、プライベートIP拒否、リダイレクト検査）
  - defusedxml による XML 攻撃緩和、レスポンスサイズ制限
  - DuckDB へバルク挿入（トランザクション・チャンク処理）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit の多層スキーマ定義
  - 初期化ユーティリティ（init_schema、init_audit_db）
  - インデックス・制約を含む冪等DDL

- ETLパイプライン
  - 差分更新（最終取得日基準）、バックフィル、カレンダー先読み
  - データ保存と品質チェックの統合（quality モジュール）
  - run_daily_etl による日次一括処理

- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比閾値）、重複、日付整合性チェック
  - QualityIssue を返し、重大度に基づいた判断が可能

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティテーブル群
  - UUID を用いた冪等キーとステータス管理
  - UTCタイムゾーン固定

---

## セットアップ手順（ローカル開発）

前提: Python 3.9+（コードは型注釈等を使用）。DuckDB, defusedxml などの依存が必要です。

1. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   - 最低限の依存例:
     ```
     pip install duckdb defusedxml
     ```
   - 開発パッケージがあればプロジェクトの requirements.txt / pyproject.toml に従ってください。
   - パッケージを開発モードでインストールする場合:
     ```
     pip install -e .
     ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると、自動的に読み込まれます（環境変数により自動読み込みを無効化可能）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack Bot Token（必須）
     - SLACK_CHANNEL_ID: Slack 送信先チャネルID（必須）
   - 任意・デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # パスは設定に合わせて変更
     conn.close()
     ```
   - 監査ログ用スキーマ（必要な場合）:
     ```python
     from kabusys.data import audit, schema
     conn = schema.get_connection("data/kabusys.duckdb")  # すでに init_schema を実行している前提
     audit.init_audit_schema(conn, transactional=True)
     conn.close()
     ```

---

## 使い方（主要API例）

- 設定取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- J-Quants からデータ取得（直接呼び出し）
  ```python
  from kabusys.data import jquants_client as jq
  # トークンを渡すか、settings から自動で取得される
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- DuckDB に保存（冪等）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  ```

- ニュース収集ジョブ（全ソース）
  ```python
  from kabusys.data import news_collector as nc, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  results = nc.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  # results: {source_name: saved_count}
  ```

- 日次ETL（カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data import pipeline, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ETL の差分ロジック
  - run_prices_etl/run_financials_etl/run_calendar_etl を個別で呼べます。各関数は取得件数／保存件数を返します。

---

## 動作設計上のポイント（開発者向け要約）

- レート制限: J-Quants へは 120 req/min の固定間隔スロットリングを実装（RateLimiter）。
- 冪等性: DuckDB 保存は ON CONFLICT で更新し重複を排除。
- トークン管理: ID トークンはモジュール内キャッシュ。401 を受けると一度だけリフレッシュして再試行。
- ニュース収集: URL 正規化→SHA-256（先頭32文字）で ID を生成。SSRF 対策・受信上限を実装。
- 品質チェック: Fail-fast ではなく全チェックを実行し、問題は QualityIssue オブジェクトで返す。呼び出し側が重大度に応じて停止判断を行う。
- カレンダー: market_calendar データがない場合は曜日ベースでフォールバック。DB に部分登録があるケースでも一貫した判定ができるように設計。

---

## ディレクトリ構成

プロジェクトの主要なファイル配置（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
      - (戦略実装モジュールを配置)
    - execution/
      - __init__.py
      - (発注・ブローカ連携モジュールを配置)
    - monitoring/
      - __init__.py
      - (監視・アラート関連を配置)

主に data パッケージが ETL/DB/取得ロジックを提供し、strategy / execution / monitoring は上位レイヤー（戦略ロジックや発注・監視）用のプレースホルダ／将来実装箇所です。

---

## 注意事項 / 運用上のヒント

- 環境変数の自動読み込み:
  - .env と .env.local をプロジェクトルートから自動読み込みします。優先順位は OS 環境 > .env.local > .env。
  - テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化できます。
- DB 初期化:
  - 初回は schema.init_schema() を実行してテーブルを作成してください。init_schema は冪等なので何度実行しても安全です。
- ログ:
  - settings.log_level でログレベルを制御します。運用では INFO か WARNING、トラブルシュート時に DEBUG を使用してください。
- セキュリティ:
  - news_collector は SSRF や XML 攻撃対策を実装していますが、追加のネットワークポリシー（プロキシやファイアウォール）も検討してください。
- テスト:
  - jquants_client の _urlopen や news_collector の HTTP層はモック差し替え可能な実装となっています。ユニットテストで外部呼び出しを置き換えてください。

---

必要であれば、README に以下を追加できます:
- 詳細な .env.example ファイル
- よくあるトラブルシュート（認証エラー、DB ロック、ネットワークタイムアウト）
- CI / デプロイ手順（Dockerfile 例、systemd サービス例）
- strategy / execution 用の API サンプル（シグナル生成→order_requests 登録 → 発注ハンドラのフロー）

追加で盛り込みたい項目があれば教えてください。