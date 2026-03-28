# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、投資運用システムに必要なユーティリティ群を提供します。

---

## 主要な特徴（Features）

- データ取得・ETL
  - J-Quants API から株価日足・財務・マーケットカレンダーの差分取得と冪等保存
  - DuckDB への効率的な保存ロジック（ON CONFLICT DO UPDATE）
- ニュース収集・NLP
  - RSS フィードの安全な収集（SSRF・gzip制限・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント (ai_scores) の生成
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成し日次で 'bull' / 'neutral' / 'bear' 判定
- Research ツール
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算・IC（Spearman）・ファクター統計サマリ
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue オブジェクトで結果を返す）
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までトレーサビリティを取る監査テーブルの初期化ユーティリティ
- 設定管理
  - .env / 環境変数の自動読み込み（パッケージ配置後も問題なく動作するルート探索）

---

## サポートされる Python バージョン

- Python 3.10+（PEP 604 の型ヒントなどを使用）

---

## 必要な依存パッケージ（主なもの）

- duckdb
- openai
- defusedxml

（プロジェクトルートに requirements.txt がある想定で pip install してください。なければ上記を個別にインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン・移動
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存関係をインストール
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 最小限:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発モードでインストール（パッケージ内で利用する場合）:
     ```bash
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（config.Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知用途）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で利用）
   - 任意（デフォルトがあるもの）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | …) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   - 例: `.env`（最小）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（代表的な例）

ここでは主要なユーティリティの簡単な利用例を示します。実運用ではログ設定やエラーハンドリングを適切に組み込んでください。

- 共通: DuckDB 接続を作成して関数に渡す
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

1) 日次 ETL を実行する（市場カレンダー・株価・財務を取得し品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日（環境で調整）を使用
  print(result.to_dict())
  ```

2) ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # 明示的に API キーを渡すことも可能（None なら環境変数 OPENAI_API_KEY を使用）
  wrote_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"wrote {wrote_count} scores")
  ```

3) 市場レジーム（bull/neutral/bear）を計算して market_regime に書き込む
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

4) 監査ログ用の別 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブル等が作成される
  ```

5) カレンダー更新ジョブのみ実行
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn)
  print(f"saved {saved} calendar records")
  ```

---

## ディレクトリ構成（主要ファイル）

パッケージルート: src/kabusys 以下

- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング、score_news を提供
  - regime_detector.py — マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — 日次 ETL のエントリポイントと個別 ETL ジョブ
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - news_collector.py — RSS 収集と前処理
  - quality.py — データ品質チェック（各チェック関数）
  - stats.py — 汎用統計ユーティリティ（zscore 正規化）
  - audit.py — 監査ログの DDL 定義・初期化
  - etl.py — ETLResult の公開再エクスポート
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility 等
  - feature_exploration.py — 将来リターン、IC、統計サマリ等

（上記は主要なモジュールのみ抜粋。実際のリポジトリには他の補助モジュール・テスト等が存在する場合があります。）

---

## 開発上の注意 / 設計方針（概要）

- ルックアヘッドバイアス防止:
  - 各モジュールは date / target_date を明示的に受け取り、内部で date.today() を参照しないように設計されています（バックテストでの安全性向上）。
- 冪等性:
  - ETL や保存処理は基本的に冪等（ON CONFLICT や DELETE→INSERT など）で実装されています。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は部分的にフォールバックして処理を継続する設計（ログ記録のうえゼロレンダリングやスキップする等）。
- セキュリティ:
  - RSS 収集では SSRF 対策、defusedxml を利用した XML パース、安全な URL 正規化などを実施。

---

## テスト / ローカル実行補助

- 自動 env 読み込みを無効化する（テストで環境を制御したい場合）:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- news_nlp / regime_detector の OpenAI 呼び出しは内部で _call_openai_api を抽象化しており、unittest.mock.patch で差し替えてテスト可能です。

---

必要であれば、README に以下を追加できます:
- 詳細な .env.example（各環境変数の説明）
- CI / デプロイ手順（Airflow / cron での ETL スケジューリング例）
- Schema（DuckDB テーブル定義の抜粋）
- 実運用での注意点（API レート制限やコスト管理、OpenAI のレスポンス検証方針）

追加の内容や出力形式の指定があれば教えてください。README を拡張して作成します。