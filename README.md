# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データの取得（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）、研究用ファクター計算などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ基盤と研究/自動売買のための共通ユーティリティ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーデータの差分取得と DuckDB への冪等保存（ETL）
- ニュース収集・前処理・LLM（OpenAI）による銘柄単位のセンチメントスコア付与
- ETF（1321）の移動平均乖離とマクロニュースから市場レジームを判定
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions）用スキーマ初期化
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と評価ユーティリティ

設計上、以下を重視しています。
- ルックアヘッドバイアスの回避（内部で date.today() を不用意に参照しない）
- 冪等性（DB保存は更新可能な形で実装）
- フェイルセーフ（外部API失敗時は明確なフォールバック／ログ出力）
- DuckDB を中心とした軽量なオンディスク分析基盤

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、上場情報、カレンダー取得
  - 差分取得ロジック・レートリミッター・自動トークンリフレッシュ・リトライ実装
  - ETL の統合エントリ（run_daily_etl）と個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック
  - 欠損データ検出、重複検出、スパイク検出、日付整合性チェック
- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策・gzip処理・URL正規化）
  - raw_news / news_symbols への冪等保存ロジック
- ニュース NLP（OpenAI）
  - 銘柄単位のセンチメント付与（gpt-4o-mini を想定）: score_news
  - マクロニュースを用いた市場レジーム判定: score_regime
- 研究用モジュール
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリ
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化関数（init_audit_schema / init_audit_db）

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 の型記法（|）等を使用）
- 必須パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

pip 例:
- pip install duckdb openai defusedxml

プロジェクトとしてパッケージ化されている場合は:
- pip install -e . など

（実際の requirements.txt は本コード断片に含まれていません。環境に応じて追加の依存をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix/macOS) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他のパッケージを追加）
4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（注意: 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数の例は次節参照
5. DuckDB ファイルや監査DBの配置（初期化はアプリから行える）
   - デフォルトの DuckDB 保存場所は data/kabusys.duckdb（settings.duckdb_path）
   - 監査ログ専用 DB を別途初期化したい場合は init_audit_db を使用

必須環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API パスワード（実行モジュール等で使用）
- SLACK_BOT_TOKEN: Slack 通知用（必要な場合）
- SLACK_CHANNEL_ID: Slack channel ID（必要な場合）
- （オプション）KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパスの上書き

.example .env:
（プロジェクトルートに `.env.example` を置く想定）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（サンプル）

以下は代表的な利用例です。実運用前に必ず必要な環境変数と DB スキーマを用意してください。

- DuckDB 接続と ETL 実行（日次ETL）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # 設定に従い今日の日付で ETL を実行
print(result.to_dict())
```

- ニュース NLP スコア付与（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB（audit）初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DuckDB ファイルを作成・初期化
conn = init_audit_db(settings.duckdb_path)
# conn 上で signal_events / order_requests / executions テーブルが利用可能
```

- 研究モジュールの利用例（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- OpenAI 呼び出しは API 利用料金が発生します。APIキーの管理と使用回数に注意してください。
- ETL は J-Quants API レート制限を守る実装ですが、ID トークンやネットワークの状態に応じたエラーハンドリングが行われます。
- 自動で .env を読み込む仕組みがあります（config.py）。テスト時等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋。実プロジェクトはさらにドキュメント・スクリプト等が存在する場合があります。）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py          # ニュースを集約して OpenAI に投げ、ai_scores テーブルへ書き込む
      - regime_detector.py   # ETF 1321 の MA とマクロニュースで市場レジームを判定
    - data/
      - __init__.py
      - jquants_client.py    # J-Quants API クライアント（取得 / 保存 ロジック）
      - pipeline.py          # ETL パイプラインと個別 ETL ジョブ
      - etl.py               # ETLResult を再エクスポート
      - quality.py           # データ品質チェック
      - calendar_management.py
      - news_collector.py    # RSS 取得・前処理・保存
      - stats.py             # 共通統計ユーティリティ（zscore 正規化等）
      - audit.py             # 監査ログスキーマの DDL と初期化関数
    - research/
      - __init__.py
      - factor_research.py   # momentum / value / volatility ファクター
      - feature_exploration.py  # 将来リターン・IC・統計サマリ等
    - monitoring/            # （コードベースに含まれている可能性のある監視モジュール）
    - execution/             # （発注・ブローカー統合用モジュール）
    - strategy/              # （戦略実装用モジュール）
    - monitoring/            # （監視/Slack通知等）

各ファイルはモジュール単位で役割が分かれており、DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取る関数が多く、テストや再利用がしやすい設計になっています。

---

## 開発・テストに関する注意

- 自動 .env ロードはプロジェクトルート（.git もしくは pyproject.toml の存在する親ディレクトリ）を基準に実行されます。
- テスト実行時、環境変数や API 呼び出し（OpenAI / J-Quants / 外部 RSS）をモックすることを推奨します。コード中に unittest.mock.patch を想定した差替箇所（_call_openai_api 等）があります。
- DuckDB の executemany は空リストを許容しないバージョン差を考慮した実装がされています（実行前に空チェックが行われています）。

---

必要であれば、README に含める具体的なコマンド（セットアップ用スクリプト、cron / Airflow ジョブの例、SQL スキーマ初期化手順）や .env.example をさらに詳しく作成します。どの情報を優先的に追記しますか？