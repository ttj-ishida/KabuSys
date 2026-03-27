# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの差分取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージ群です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と OpenAI を用いた銘柄別/マクロセンチメントのスコアリング
- ファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量解析ユーティリティ
- 監査ログ用スキーマ（signal / order_request / executions）と初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数ベースの設定管理（.env 自動読み込み）

設計上、バックテスト時の「ルックアヘッドバイアス」を避けるため、内部で `date.today()` を不用意に参照しない設計を心がけています。また、外部 API 呼び出しは適切にリトライやレート制御を行うフェイルセーフ実装です。

---

## 機能一覧

- 環境設定読み込み（.env / .env.local 自動読み込み。無効化フラグあり）
- J-Quants クライアント
  - 株価日足、財務データ、上場銘柄情報、マーケットカレンダーの取得
  - DuckDB への冪等保存（ON CONFLICT）
  - レート制限、トークン自動リフレッシュ、リトライ
- ETL
  - 差分取得（backfill オプション）
  - 日次 ETL 実行 run_daily_etl
  - ETL 結果を ETLResult で集約
- データ品質チェック（quality.run_all_checks 等）
- ニュース収集（RSS）と前処理、SSRF 対策、サイズ制限
- ニュース NLP（OpenAI）
  - 銘柄別センチメント score_news
  - マクロセンチメントと MA200 を合成した市場レジーム判定 score_regime
- 研究用ユーティリティ（research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- 監査ログスキーマ初期化（data.audit.init_audit_db / init_audit_schema）

---

## セットアップ手順

1. リポジトリをクローン（例）
   - git clone <リポジトリ URL>

2. Python 環境を準備
   - 推奨: Python 3.10+（パッケージの型注釈に依存）

3. 必要パッケージをインストール（例）
   - pip install -r requirements.txt
   - （requirements.txt が無い場合の主要依存）
     - duckdb
     - openai
     - defusedxml

   - 開発時は editable install:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注系を使う場合）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合
   - SLACK_CHANNEL_ID — Slack 通知先チャンネル
   - OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定を使う場合）

   任意（デフォルトあり）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C......
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化（監査ログ）
   - Python スクリプトから初期化できます（例は次節）。

---

## 使い方（主な例）

以下はパッケージをインポートして主要処理を実行するサンプルコードの例です。

- DuckDB 接続を作成して日次 ETL を実行する例
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 監査ログ専用 DB を初期化する（ファイル生成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# 必要なら conn を使って監査テーブルにアクセス
```

- ニュースセンチメント（指定日）の計算
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（MA200 とマクロセンチメントの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算（モメンタム等）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は dict のリスト（各要素に date, code, mom_1m など）
```

- データ品質チェックを走らせる
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意:
- OpenAI を使う関数は環境変数 OPENAI_API_KEY または api_key 引数でキーを渡してください。
- DuckDB のタイムゾーンや接続コンテキストは呼び出し側で管理してください（audit.init_audit_schema は UTC に設定します）。

---

## ディレクトリ構成

主要モジュールと目的を簡潔に示します（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py  — 環境変数読み込み・設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの銘柄別センチメント（score_news）
    - regime_detector.py — マクロセンチメントと MA200 を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL の公開インターフェース（ETLResult 再エクスポート）
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / サマリー統計
  - ai、data、research 以下にさらに内部ユーティリティや補助関数が実装されています。

---

## 注意点 / 運用メモ

- 自動で .env を読み込みますが、CI やテストで不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはリトライやフォールバックを実装していますが、API コスト・レート制限に注意してください（バッチ呼び出し、チャンク処理あり）。
- J-Quants API 呼び出しはレートリミット（120 req/min）に合わせた固定間隔レートリミッタとリトライを実装しています。
- DuckDB のバージョン差異により executemany の挙動が変わる箇所があります（コード中で対応済み）。
- 本ライブラリは実際の売買系ロジック（kabu ステーションへの発注フロー）を含みます。実運用（live）モードでの動作は慎重に検証・監査ログの確認を行ってください。

---

もし README に追加したい具体的な使用例（バックテスト用のサンプル、CI 用のコマンド、.env.example の完全テンプレートなど）があれば教えてください。必要に応じて追記・整形します。