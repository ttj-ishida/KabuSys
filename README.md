# KabuSys

日本株向けのデータパイプライン・リサーチ・市場センチメント解析・監査ログを備えた自動売買（バックオフィス/研究用）ライブラリ群です。DuckDB をデータ層に利用し、J-Quants / JPEX（マーケットカレンダー）や RSS、OpenAI を使ったニュース NLP、ファクター計算、ETL パイプラインなどを包含します。

主な設計方針
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない設計箇所が多い）
- DuckDB を用いたローカル分析・ETL（冪等保存）
- 外部 API 呼び出しに対する堅牢なリトライ／フェイルセーフ実装
- 監査ログ（信号→発注→約定のトレース）を充実

---

## 機能一覧

- 環境変数/設定管理（自動 .env 読み込み、保護キー対応）
- J-Quants API クライアント
  - 株価（日足 OHLCV）、財務データ、上場銘柄情報、マーケットカレンダーの取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL（価格、財務、カレンダー）
  - 品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、受信サイズ制限）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄単位のニュース統合センチメント（ai_scores へ書き込み）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM を合成）
  - JSON Mode + レスポンス検証、リトライ対策
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマン）、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化（監査証跡）
  - init_audit_db による DuckDB 初期化ユーティリティ

---

## 必要条件

- Python 3.10 以上（型記法（|）などで 3.10+ が必要）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（他、標準ライブラリの urllib 等を使用）

推奨：仮想環境を用いること。

---

## セットアップ手順

1. リポジトリをクローン／ソースを用意
   - 例: git clone ...

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使用）

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例 `.env`（最小例 — 実運用では適切に設定してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 注意: config.Settings に必須とされるキー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時 ValueError を投げます。
   - OPENAI_API_KEY は AI モジュール（news_nlp / regime_detector）で使用します。関数呼び出し時に api_key を渡すことも可能です。

5. データベース初期化（監査ログ等）
   - 監査ログ用 DB を作る:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - その他テーブル（raw_prices/raw_financials/market_calendar/raw_news 等）のスキーマ作成は、プロジェクト内のスキーマ初期化ユーティリティ（存在する場合）を実行してください。監査スキーマは上記で初期化されます。

---

## 使い方（例）

ここでは主要なユースケースを簡単に示します。実行は Python スクリプトや cron / Airflow 等から呼び出す運用が想定されます。

1. DuckDB に接続して日次 ETL を実行
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

2. ニュース NLP（当日対象のニュースを集計して ai_scores に保存）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を渡すか、OPENAI_API_KEY 環境変数を設定
print(f"written scores: {written}")
```

3. 市場レジーム（ma200 + マクロニュース）を判定して保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4. 監査DB初期化（再掲）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

5. 個別ファクター計算（リサーチ）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意点
- OpenAI への API 呼び出しは gpt-4o-mini を使う想定です。API 利用料・レート制限に注意してください。
- ETL / AI 呼び出しは外部 API を使うため、ネットワークエラー・APIエラー時の例外やフェイルセーフの振る舞いをログで確認してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、関数群では空チェックを行っています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・.env 自動読み込み・設定アクセスラッパー（settings）
- ai/
  - __init__.py
  - news_nlp.py       — ニュースを統合して銘柄別センチメントを計算、ai_scores へ書き込み
  - regime_detector.py— ETF(ma200) とマクロニュース（LLM）を合成し market_regime を作成
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、取得 + DuckDB への保存
  - pipeline.py       — ETL の実行ロジック（run_daily_etl, run_prices_etl など）
  - etl.py            — ETLResult の公開（再エクスポート）
  - stats.py          — zscore_normalize 等の統計ユーティリティ
  - quality.py        — データ品質チェック（欠損、スパイク、重複、日付整合性）
  - calendar_management.py — 市場カレンダー管理（営業日判定、next/prev/get）
  - news_collector.py — RSS 取得・前処理・DB への保存（SSRF対策、gzip 対応等）
  - audit.py          — 監査ログテーブル定義・初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility の計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー 等

（パッケージ全体には strategy / execution / monitoring などの名前が __all__ に挙がっていますが、本スニペットでは上記が主に実装されています）

---

## 運用上の注意 / ベストプラクティス

- 環境変数には機密情報（API トークン等）が含まれるため、リポジトリにコミットしないでください。`.env.example` を作り設定項目を示す運用が推奨されます。
- ETL や AI 呼び出しは外部 API に依存するため、監視・リトライ・アラート（例: Slack 経由通知）を導入してください（Slack 用設定は config で想定されています）。
- DuckDB ファイルのバックアップ・ローテーションと、監査ログの永続化方針を明確にしてください。
- テスト時に .env の自動読み込みが邪魔なら環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を有効にしてください。
- Look-ahead バイアスに注意して、バックテスト用途では ETL の実行タイミングとデータの取得タイミング（fetched_at）を確認してください。

---

README に書かれている以外にも、各モジュールには詳細な docstring が含まれているため、利用時は該当モジュールの関数 docstring を参照してください。必要であれば README に追加したいサンプルや運用手順（Airflow / cron 設定例、Slack 通知例、DB スキーマ初期化スクリプトなど）をお作りします。どの情報を追記しますか？