# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
J-Quants からのデータ取得・ETL、ニュース収集・LLM を用いたニュース NLP、研究用ファクター計算、監査ログスキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の用途を想定した Python ライブラリです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への永続化（ETL）
- RSS ベースのニュース収集と前処理（SSRF対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント分析 / 市場レジーム判定
- 研究用途のファクター計算、将来リターン・IC 計算などのユーティリティ
- 取引フローのトレーサビリティを担保する監査ログ（DuckDB スキーマ）初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計は「ルックアヘッドバイアス防止」「冪等性」「堅牢なネットワークリトライ／レート制御」「テスト容易性」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動更新・DuckDB 保存）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得 → 前処理 → raw_news への保存（SSRF 対策・トラッキング除去）
  - calendar_management: JPX カレンダー取得 / 営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログテーブルと初期化ユーティリティ（init_audit_db / init_audit_schema）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp: ニュースを銘柄ごとに集約して LLM に送りセンチメントを ai_scores に保存（score_news）
  - regime_detector: ETF 1321 の MA200 とマクロニュース LLM スコアを合成して市場レジームを判定（score_regime）
- research/
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリーなど
- config:
  - 環境変数読み込み（.env / .env.local 自動ロード）と設定ラッパー（settings）

---

## 前提・必須環境

- Python 3.10 以上（型注釈の union 演算子（A | B）等を使用）
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （その他：標準ライブラリ以外に必要なライブラリがあれば pyproject.toml / requirements.txt を参照してください）

例（最小インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt / pyproject.toml があればそれを用いる
```

---

## 環境変数 / 設定

config.Settings 経由で各種設定値を取得します。主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: 環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  OS 環境 > .env.local > .env の順でロードします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意:
- OpenAI API キーは ai モジュールの関数（score_news, score_regime）に api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定します。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境と依存パッケージのインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .    # パッケージが pyproject.toml / setup.cfg を持つ場合
   # あるいは個別に
   pip install duckdb openai defusedxml
   ```

3. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を作成し、必要なキーを設定します。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     OPENAI_API_KEY=sk-xxx
     SLACK_BOT_TOKEN=xoxb-xxx
     SLACK_CHANNEL_ID=CXXXXX
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主なエントリポイント）

以下はライブラリをインポートして直接利用する最小例です。実運用ではログ設定や例外ハンドリング等を適切に行ってください。

- DuckDB 接続を作成:
  ```
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl がメイン）
  ```
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai/news_nlp.score_news）
  ```
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("written:", n_written)
  ```

- 市場レジーム判定（ai/regime_detector.score_regime）
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ DB の初期化（audit スキーマ）
  ```
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は UTC タイムゾーン設定とテーブル/インデックス作成を行う
  ```

- 研究用ファクター計算
  ```
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  ```

---

## 開発向けの注意点 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - モジュールの多くは内部で datetime.today() / date.today() を直接参照せず、target_date 引数を明示して処理を行います（バックテストや再現性のため）。
- 冪等性:
  - J-Quants から取得したデータは DuckDB に ON CONFLICT DO UPDATE 相当で保存され、再実行で重複しません。
- ネットワーク堅牢性:
  - J-Quants クライアントや OpenAI 呼び出しにはリトライ・バックオフ・レート制御が実装されています。
- セキュリティ:
  - news_collector は SSRF 対策（プライベートアドレス拒否、リダイレクト検査）、defusedxml を使用した XML パース、最大受信バイト数制限等を実施しています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                       - 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    - ニュース NLP / score_news
    - regime_detector.py             - 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py                    - ETL パイプライン (run_daily_etl 等)
    - etl.py                         - ETLResult の公開
    - news_collector.py              - RSS 収集・前処理
    - calendar_management.py         - マーケットカレンダー管理 / 営業日判定
    - quality.py                     - データ品質チェック
    - audit.py                       - 監査ログスキーマ初期化 (init_audit_db)
    - stats.py                       - zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py             - Momentum / Value / Volatility 等
    - feature_exploration.py         - 将来リターン / IC / 統計サマリー

---

## よくある操作例（スニペットまとめ）

- .env 自動ロードを無効にしてテストを行う:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- DuckDB に直接クエリを投げる（例: raw_prices の最新日を確認）:
  ```
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  print(conn.execute("SELECT MAX(date) FROM raw_prices").fetchone())
  ```

---

## ライセンス・貢献

（リポジトリに LICENSE / CONTRIBUTING があればそれに従ってください）

---

README はプロジェクトの導入・理解を手早くするための概要です。より詳しい設計・仕様（DataPlatform.md, StrategyModel.md 等）やテストコード、CI 設定がある場合は併せて参照してください。必要であれば、README に実行可能なワークフロー（例: GitHub Actions での ETL スケジュール、Slack 通知例）を追記します。