# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは日本株向け自動売買／データプラットフォームのコアライブラリ群です。ETL、ニュース収集・NLP、マーケットレジーム判定、ファクター研究、監査ログ（トレーサビリティ）など、バックオフィスから戦略開発までを想定したモジュール群を含みます。

主なポイント
- DuckDB を用いたローカルデータプラット（raw_prices / raw_financials / raw_news など）
- J-Quants API 経由のデータ取得（株価・財務・市場カレンダー）
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント評価
- ETF（1321）MA ベースとマクロニュースでの市場レジーム判定
- 研究用ファクター群（モメンタム / バリュー / ボラティリティ）と統計ユーティリティ
- 監査ログ（signal → order_request → executions）を保持する監査スキーマ

---

## 機能一覧

- データ取得・ETL
  - J-Quants API からの株価日足、財務データ、マーケットカレンダーの差分取得（pagination / retry / rate limit 対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS 取得、前処理、raw_news 保存（SSRF・Gzip・XML 攻撃対策）
  - 銘柄紐付け（news_symbols 経由）
  - OpenAI（gpt-4o-mini）の JSON mode を使った銘柄別センチメント・バッチ処理（score_news）

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースセンチメントを合成して日次で 'bull'/'neutral'/'bear' を判定（score_regime）

- 研究（Research）
  - モメンタム / バリュー / ボラティリティファクター計算
  - 将来リターン計算、IC（Information Coefficient）、Z-score 正規化など

- 監査・トレーサビリティ
  - signal_events / order_requests / executions テーブルの初期化とインデックス作成（init_audit_schema / init_audit_db）
  - 発注フローの監査ログ管理（order_request_id を冪等キーとして利用）

---

## セットアップ手順（開発環境向け）

前提
- Python 3.10+（型アノテーションの union 型や型注釈が使用されています）
- ネットワークアクセス（J-Quants, RSS, OpenAI）

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 開発インストール（パッケージ化されている場合）
   ```
   pip install -e .
   ```
   もし pyproject.toml / requirements.txt がない場合は主要依存を個別に入れてください:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（あるいは `.env.local`）を置くと自動でロードされます。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_station_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567

   任意／デフォルトあり:
   - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
   - LOG_LEVEL=INFO | DEBUG | ...
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動 env ロードを無効化）
   - KABUSYS_OPENAI_API_KEY や OPENAI_API_KEY は OpenAI 呼び出し時に引数で渡すか環境変数を利用

   データベースパス
   - DUCKDB_PATH=data/kabusys.duckdb  （settings.duckdb_path）
   - SQLITE_PATH=data/monitoring.db

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な関数 / ワークフローの例）

ここではライブラリ関数を直接呼ぶ例を示します。用途に応じてスケジューラ（cron / Airflow / Prefect 等）やアプリケーションから利用してください。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 監査DB を初期化する（専用 DB に監査スキーマを作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db(settings.duckdb_path)  # ":memory:" も可
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI の API キーは環境変数 OPENAI_API_KEY で渡すか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジームを判定して market_regime テーブルへ書き込む
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  factors = calc_momentum(conn, target_date=date(2026, 3, 20))
  # factors は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
  ```

- Z-score 正規化ユーティリティ
  ```python
  from kabusys.data.stats import zscore_normalize

  normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

注意点
- OpenAI 呼び出しは外部 API を利用するため呼び出し回数に応じてコストが発生します。API キー管理／レート制御に注意してください。
- データ取得はレート制限やリトライロジックを備えていますが、ネットワーク障害時はログを確認してください。
- 各モジュールは「ルックアヘッドバイアス」を避ける設計思想で書かれています（内部で date.today() や datetime.now() を使わない等）。バックテストで使う場合は必ず target_date を明示してください。

---

## 主要ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py: パッケージ初期化（version 定義）
  - config.py: 環境変数・設定管理（自動 .env ロード・settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースの OpenAI スコアリング（score_news）
    - regime_detector.py: 市場レジーム判定ロジック（score_regime）
  - data/
    - __init__.py
    - calendar_management.py: マーケットカレンダー管理・営業日ロジック
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - jquants_client.py: J-Quants API クライアント（fetch / save / auth / rate limit）
    - news_collector.py: RSS 取得と保存ロジック（SSRF 対策など）
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py: 汎用統計ユーティリティ（zscore_normalize）
    - audit.py: 監査ログ（signal / order_requests / executions）スキーマ定義・初期化
    - etl.py: ETLResult の公開（エイリアス）
  - research/
    - __init__.py
    - factor_research.py: モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py: 将来リターン / IC / 統計サマリー等
  - ai, data, research 以下に細かな関数群が実装されています（上記が主要ファイル）

---

## 環境変数と設定（要約）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーションAPI パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須): Slack 通知用
- OPENAI_API_KEY (推奨): OpenAI API キー（score_news / regime_detector で使用）
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパス（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live（validation あり）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

自動的に .env/.env.local をプロジェクトルートから読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。

---

## テスト・開発メモ

- OpenAI 呼び出しはテストでモック可能（各モジュール内の _call_openai_api を patch して置き換えられるよう設計）
- news_collector はネットワーク・XML の攻撃に対する対策を施しています。テスト時は fetch_rss のネットワーク呼び出しをモックしてください。
- DuckDB の executemany に対する互換性（空リスト不可等）をコード内で考慮しています。テスト時は小さなデータセットで検証してください。

---

もし README に追加したい「サンプル .env.example」や「CLI 実行スクリプト」「デプロイ手順（本番・paper_trading 用）」などがあれば、その情報を教えてください。README をそれに合わせて拡張します。