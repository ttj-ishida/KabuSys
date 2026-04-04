# KabuSys

日本株向け自動売買／データプラットフォームのライブラリ群です。  
本リポジトリはデータ収集（J-Quants / RSS）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を備えた内部ライブラリです：

- J-Quants API からの株価・財務・市場カレンダーの差分取得および DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 相当）を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム（bull / neutral / bear）判定の処理（ETF 1321 の MA200 乖離 + マクロセンチメント合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を格納するスキーマの初期化ユーティリティ
- 環境変数／設定管理（.env 自動読み込み・安全な挙動）

設計方針として、ルックアヘッドバイアスを避けるために内部で datetime.today() 等を直接参照しない設計や、API 呼び出しでの堅牢なリトライ／バックオフ処理、DuckDB への冪等保存を重視しています。

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai:
  - ニュース NLP（score_news）
  - 市場レジーム判定（score_regime）
- research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - 環境変数読み込みと Settings（settings オブジェクト経由で各種設定参照）
  - .env 自動読み込み（プロジェクトルート検出、.env / .env.local の読み込み順序）
- audit:
  - 監査ログ用 DuckDB 初期化（テーブル / インデックス作成）

---

## 必要要件（推奨）

- Python 3.10+
- 主要 Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトで使用する仮想環境に合わせて適宜パッケージを追加してください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 他にテスト用ツールなどを追加してください
```

---

## 環境変数（主なもの）

本ライブラリは環境変数（または .env/.env.local）を用いて各種設定を行います。主要なキーは以下の通りです。

必須（稼働に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（ETL で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 系に使用）

OpenAI / 通知等（オプションだが多くの機能で必要）:
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime など）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用（任意）
- LINE_USER_ID: LINE 送信先ユーザ（任意）

DB / ファイルパス（デフォルトあり）:
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視制御用

ランタイム制御:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト等で便利）

※ .env.example がある想定で、それを元に .env を作成してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   必要なパッケージをインストールしてください（プロジェクトに requirements.txt があればそれを使用）。
   例:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   プロジェクトルートに .env（および必要なら .env.local）を作成し、上記の必須キーを設定します。
   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

   注意: .env.local は .env を上書きするため、秘密値やローカル差分は .env.local に置いてください。

5. DB ディレクトリなどを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（コード例）

以下は主要なユースケースの最小例です。すべて Python スクリプト内で呼び出せます。

1) DuckDB 接続を作成して ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使用する場合:
# from kabusys.config import settings
# conn = duckdb.connect(str(settings.duckdb_path))

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアリングする（OpenAI API キー必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", written)
```

3) 市場レジームを判定して保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

# :memory: でインメモリ DB も可能
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

5) 研究用ユーティリティの利用例（モメンタム計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
rows = calc_momentum(conn, target_date=date(2026,3,20))
print(len(rows), "銘柄分の結果")
```

---

## テスト・開発上のヒント

- .env 自動ロードを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。
- OpenAI 呼び出しや外部 API 呼び出しは各モジュールで分離されており、関数単位でモック可能です。ユニットテストではモックして副作用を防いでください。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")
- DuckDB は単一ファイルなので開発時は :memory: を使うと便利です。
- J-Quants API のレート制限やトークン更新は jquants_client 内で制御されていますが、実運用では id_token や refresh_token の管理に注意してください。

---

## ディレクトリ構成

以下は主要ファイル／モジュールのツリー（src/kabusys 以下）です。実際のパッケージに合わせて若干の差異がある場合があります。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（銘柄別）
    - regime_detector.py     # 市場レジーム判定（ETF 1321 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py # 市場カレンダー管理（is_trading_day 等）
    - etl.py                 # ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py            # 日次 ETL パイプライン（run_daily_etl など）
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - quality.py             # データ品質チェック
    - audit.py               # 監査ログスキーマ初期化
    - jquants_client.py      # J-Quants API クライアント（fetch/save）
    - news_collector.py      # RSS ニュース取得／前処理
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算（Momentum / Value / Volatility）
    - feature_exploration.py # 将来リターン / IC / 統計サマリー 等

---

## 注意事項 / 制約

- 本ライブラリはバックテストやリアル運用での Look-ahead バイアス防止に注意して設計されていますが、呼び出し方次第でバイアスが入る可能性があります。特にデータ取得タイミング（fetched_at）や target_date の扱いに注意してください。
- OpenAI / J-Quants 等外部 API の利用には API キーやレート制限の管理が必要です。実際の運用ではシークレット管理・監視を行ってください。
- DuckDB の executemany による空リストバインド等、バージョン依存の挙動に注意しています。DuckDB のバージョンによる差異がある場合はアップストリームのドキュメントを参照してください。

---

もし README に追加したい具体的な利用シナリオ（例: バッチの cron 設定、LINE 通知の設定例、kabuステーションとの実取引フロー）や、requirements.txt / example .env を含めてほしい場合は、その内容を教えてください。README をそれに応じて拡充します。