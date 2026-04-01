# KabuSys

日本株向けのデータプラットフォーム＋自動売買支援ライブラリです。J-Quants / JPX / RSS 等からデータを集約・品質チェックし、ファクター計算やニュースセンチメント、マーケットレジーム判定、監査ログ（注文→約定トレース）を行うことを目的とします。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数（主な設定）
- ディレクトリ構成

---

プロジェクト概要
- データ収集（J-Quants API の株価・財務・カレンダー、RSS ニュース）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュースの LLM ベースセンチメント評価（gpt-4o-mini を想定）
- 市場レジーム判定（ETF の MA とマクロニュースを組合せ）
- ファクター計算 / 特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログスキーマ（signal → order_request → execution の追跡用 DuckDB テーブル）
- DuckDB を中心としたオンプレ/ローカル分析基盤

主な機能一覧（モジュール）
- kabusys.config
  - .env 自動読み込み、Settings オブジェクトによる環境変数管理
- kabusys.data
  - jquants_client: J-Quants API 呼び出し、取得データの保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline / etl: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - quality: ETL 後のデータ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 取得 → raw_news 保存（SSRF 対策、トラッキング除去等）
  - calendar_management: 営業日判定、next/prev/get_trading_days、calendar_update_job
  - audit: 監査ログテーブル初期化・専用 DB 初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime を算出・保存
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なライブラリをインストール
   - 必須（代表例）:
     - duckdb
     - openai
     - defusedxml
   例:
   - pip install duckdb openai defusedxml

   （本リポジトリに requirements.txt がある場合は pip install -r requirements.txt を利用してください）

3. パッケージをインストール（編集可能に）
   - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（kabusys.config の自動読み込み）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須例 (.env):
     JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     OPENAI_API_KEY=<your_openai_api_key>
     KABU_API_PASSWORD=<kabu_api_password>            # kabuステーション連携用
     SLACK_BOT_TOKEN=<slack_bot_token>
     SLACK_CHANNEL_ID=<slack_channel_id>

   - 省略可能な設定例（デフォルト値が設定されています）:
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

使い方（簡単なコード例 / ワークフロー）

1) DuckDB 接続を用意する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) ETL（デイリー）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニューススコア計算（LLM）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 第2引数に api_key を渡すことも可能（環境変数 OPENAI_API_KEY が使われます）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

6) 監査ログスキーマの初期化（監査専用 DB を生成する）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を利用して order / signal を記録する処理に接続できます
```

注意:
- LLM 呼び出しは OpenAI SDK（openai.OpenAI）を使っており、OpenAI API キーが必要です。api_key を関数引数で渡すか OPENAI_API_KEY 環境変数を設定してください。
- J-Quants API を利用する関数は JQUANTS_REFRESH_TOKEN（環境変数）を参照して id_token を取得します。

---

主要な環境変数（summary）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI functions): OpenAI API キー
- KABU_API_PASSWORD: kabuステーション API のパスワード（約定系連携）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知関連
- DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意): 監視用 SQLite path（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

---

ディレクトリ構成（重要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
    - (その他: ETL/utility モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージメンバとして存在が想定される)
  - strategy/ (戦略実装用フォルダ)
  - execution/ (発注実行用フォルダ)

（上記は src 配下の主要モジュールを示しています。実行時はパッケージとしてインポートしてください。）

---

運用上の注意 / 設計上のポイント
- Look-ahead バイアス対策
  - 多くのモジュールは datetime.today() や date.today() を直接参照しない設計で、target_date を明示して評価することを想定しています。バックテストでは過去の target_date を明示して呼ぶこと。
- ETL の冪等性
  - jquants_client の save_* は ON CONFLICT DO UPDATE を利用し、再実行が安全なように設計されています。
- API レート制限・リトライ
  - J-Quants リクエストはレートリミッタと再試行ロジックを持ちます。OpenAI 呼び出しもリトライ設計が組み込まれています。
- セキュリティ
  - news_collector は SSRF 防止、XML パーサの脆弱性対策（defusedxml）や応答サイズチェックを備えています。

---

よくある利用フロー（例）
1. .env を準備し必要な API キーを設定
2. データベース（DuckDB）を用意
3. run_daily_etl を Cron / Airflow 等で定期実行（夜間バッチ）
4. ETL 後に news_nlp.score_news → ai_scores を更新
5. regime_detector.score_regime による市場レジーム更新
6. 戦略層でファクター・AI スコア・レジームを組合せ、signal を生成
7. audit テーブルに signal を書き出し、order_request → execution の追跡を実装

---

サポート / 開発メモ
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効にできます。
- OpenAI 呼び出しはテスト環境でモック可能（news_nlp._call_openai_api, regime_detector._call_openai_api を patch）。
- DuckDB のバージョン依存の記述に注意（executemany の空リスト制約等、コメントに注記あり）。

---

以上。必要であれば README に
- 実行例の詳細な CLI コマンド（cron ジョブ例）
- requirements.txt の候補
- .env.example ファイル
を追加できます。どれを補足するか教えてください。