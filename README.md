# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント算出）、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理など、バックテスト／運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次バッチの統合実行（run_daily_etl）

- ニュース収集 / NLP
  - RSS フィードからニュースを収集（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント（score_news）
  - マクロニュース + ETF (1321) の MA200 乖離を組み合わせた市場レジーム判定（score_regime）

- リサーチ / ファクター
  - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20）、バリュー（PER/ROE）等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution を辿れる監査テーブル群（DuckDB）
  - 監査用スキーマ初期化ユーティリティ（init_audit_schema / init_audit_db）

- マーケットカレンダー管理
  - market_calendar テーブルを参照した営業日判定、next/prev_trading_day、期間内営業日列挙
  - J-Quants からカレンダー差分取得ジョブ（calendar_update_job）

---

## 必要条件

- Python 3.10 以上（型記法 X | Y を使用）
- DuckDB
- OpenAI Python SDK（OpenAI API を利用する場合）
- defusedxml（RSS パース時の安全対策）
- （実運用では追加で）Slack SDK、kabuステーション API クライアント等

最低限の pip インストール例:
```bash
python -m pip install "duckdb>=0.10" openai defusedxml
```
（パッケージ構成に応じて requirements.txt を用意してください）

---

## 環境変数 / .env

自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動読込を無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数:
- JQUANTS_REFRESH_TOKEN  （必須） — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      （必須） — kabuステーション API のパスワード
- KABU_API_BASE_URL      （任意、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        （必須） — Slack 通知用（利用する場合）
- SLACK_CHANNEL_ID       （必須） — Slack 通知先チャンネル ID（利用する場合）
- OPENAI_API_KEY         （OpenAI を利用する場合、score_news/score_regime のデフォルト）
- DUCKDB_PATH            （任意、デフォルト data/kabusys.duckdb）
- SQLITE_PATH            （任意、デフォルト data/monitoring.db）
- KABUSYS_ENV            （任意、development / paper_trading / live）
- LOG_LEVEL              （任意、DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 簡易インストール例:
     ```bash
     pip install -e .           # パッケージとしてインストール可能な場合
     pip install duckdb openai defusedxml
     ```
   - 実運用や CI 用に requirements.txt を用意している場合はそれを利用してください。

4. `.env` を作成して必要な環境変数を設定（.env.example があれば参照）

5. DuckDB ファイルの親ディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```

6. 監査ログ用 DB（任意）を初期化（後述の使用例参照）

---

## 使い方（よく使う API／例）

以下は最小限の利用例です。実運用ではログ設定やエラーハンドリング、ジョブスケジューラ（cron / airflow など）を併用してください。

- ETL（日次パイプライン）実行例:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントのスコア取得:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数
print("written:", written)
```
score_news は内部で OpenAI API を呼びます。`OPENAI_API_KEY` を環境変数に設定するか、api_key 引数で渡してください。

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
```

- 監査ログ DB を初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn をそのまま使って監査テーブルにログを挿入できます
```

- ファクター計算・リサーチ例:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026,3,20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

---

## 推奨ワークフロー（運用上の注意）

- ETL は日次バッチで実行し、先に calendar_etl を実行して営業日判定に使用すること。
- OpenAI 呼び出しはレート制限・失敗を考慮しており、失敗時はフェイルセーフ（スコア 0.0 等）で継続する設計です。ただし API キーやコスト管理は必ず行ってください。
- DuckDB へ大量挿入する際は ETL のトランザクションと executemany の制約に注意（コード内で考慮済み）。
- テスト時は自動的な .env 読み込みを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）と環境依存を切れます。
- 本ライブラリはバックテストループ内での直接的外部 API 呼び出し（J-Quants / OpenAI）は Look-ahead bias を生む可能性があるため避け、事前に取得・保存したデータを用いることを推奨します（設計方針に従っています）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化（__version__ 等）
- config.py — 環境変数 / 設定管理（.env 自動ロード・Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントの取得・score_news（OpenAI 使用）
  - regime_detector.py — マクロ + MA200 を組み合わせた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 / 保存 / 認証・リトライ・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl, 個別 ETL）
  - etl.py — ETLResult のエクスポート
  - news_collector.py — RSS 収集・前処理・raw_news への保存
  - calendar_management.py — マーケットカレンダー管理（営業日判定等）
  - quality.py — データ品質チェック
  - stats.py — 共通統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログ（監査スキーマ初期化 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
- （strategy / execution / monitoring 等のサブパッケージが想定されるが、実装はモジュール内をご確認ください）

---

## テスト / 開発のヒント

- OpenAI / J-Quants 呼び出しは外部依存があるため、単体テストではそれらの呼び出し部分をモックして検証してください。コード内にモックしやすいヘルパー（_call_openai_api の差し替えポイント等）が用意されています。
- DuckDB を使った単体テストは ":memory:" を指定するとインメモリ DB を利用できます（init_audit_db も対応）。
- `.env.local` を使ってローカルの機密情報を上書きする運用が可能です。

---

## ライセンス / 貢献

（必要に応じてライセンスや貢献ガイドラインを追記してください）

---

何か README に追加したい内容（例: CI 設定、具体的な schema 初期化 SQL、サンプルの .env.example）や日本語表現の修正があれば教えてください。