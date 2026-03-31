# KabuSys

日本株向けのデータプラットフォームと研究・自動売買ユーティリティ群を提供するライブラリです。J-Quants / RSS / OpenAI 等を組み合わせ、データ取得（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどを含みます。

---

## 主な特徴

- データ取得（J-Quants）と DuckDB への冪等保存（ETL）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダー等
  - ページネーション対応・トークン自動リフレッシュ・レート制御・リトライ実装
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）とニュースNLP（OpenAI を使ったセンチメント評価）
  - 銘柄別にまとめてバッチ評価、スコアを `ai_scores` に格納
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメント）
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリ、Z スコア正規化
- 監査ログスキーマ（signal / order_request / execution）を DuckDB に初期化
- 環境変数ベースの設定管理（.env 自動読み込み、.env.local 上書き）

---

## 必要条件

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

（プロジェクトに requirements.txt/pyproject.toml があればそれに従ってください）

---

## インストール

開発ディレクトリでソースを編集して使う場合の例：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# またはパッケージ化されている場合
pip install -e .
```

---

## 環境変数 / .env

プロジェクトは環境変数または .env / .env.local から設定を読み込みます。
自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。

主な環境変数（README 用に抜粋）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（LLM 呼び出しで使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード（注文連携用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（例: data/monitoring.db）
- PID_FILE_PATH — 実行プロセスの pid 保存先（例: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

自動 .env 読み込みを無効化する場合:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

.env の自動読み込み順序: OS 環境 > .env.local > .env

---

## セットアップ手順（初期化例）

1. 必要パッケージをインストール（上の手順参照）。
2. .env を作成して必要なキーを設定。
3. DuckDB を初期化（監査ログスキーマ等）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使ってさらに初期テーブルやインデックスを作成可能
```

4. ETL 用 DuckDB 接続を作成（例）:

```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

---

## 使い方（代表的な API と利用例）

以下はライブラリ内部 API を直接利用する方法の例です。運用スクリプト／ジョブで呼び出して使用します。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメントスコア）を生成

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # APIキーは環境変数 OPENAI_API_KEY から解決
print(f"scored {count} codes")
```

- マーケットレジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究系ファクター計算（例: モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト（各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev 等）
```

- 監査スキーマ初期化（既存接続に作成）

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 推奨運用パターン

- バッチで run_daily_etl をスケジューラー（cron）から日次実行。
- ニュース取得・NLP・レジーム判定は ETL 後に順次実行し、モデルやシグナル生成に利用。
- OpenAI 呼び出しのコストとレートを考慮してバッチサイズ・頻度を調整。
- 本番（実際の発注）を行う場合は KABUSYS_ENV を "live" に設定し、発注ロジックの安全性を十分検証。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 内のおもなモジュールと役割の一覧です。

- kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を作成
    - regime_detector.py — ETF (1321) MA200 とニュースを融合した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - news_collector.py — RSS 収集・前処理
    - audit.py — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記は主要モジュールの抜粋です。実際のツリーはソース内のファイルを参照してください）

---

## 注意事項 / 実装上の設計方針（抜粋）

- ルックアヘッドバイアス対策として date.today()/datetime.today() を関数内部で直接参照しない実装が多く、必ず target_date を明示的に渡して使う設計です。
- OpenAI / J-Quants 等外部 API 呼び出しにはリトライ/バックオフを実装し、API 失敗時は安全側にフォールバックするように設計されています（例: マクロ評価失敗時 macro_sentiment=0.0）。
- DuckDB への書き込みは冪等性を保つため ON CONFLICT（または executemany の個別 DELETE）を利用しています。
- ニュース収集での SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml 使用）などセキュリティ配慮が実装されています。

---

## 開発 / 貢献

- コードは単体テストやモック差し替えが容易になるように設計されています（外部呼び出し部分は差し替え可能）。
- 新機能追加・バグ修正を行う際は、既存の ETL / 品質チェック / スキーマに影響を与えないよう十分に検証してください。

---

READMEに書かれている例はライブラリ API を直接利用するサンプルであり、実運用では適切なジョブ管理・ログ・監視・権限管理（APIキーの保護）を行ってください。必要であれば、具体的な運用スクリプトや systemd / cron の例、Docker 化手順なども作成できます。必要なら教えてください。