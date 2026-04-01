# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得）、データ品質チェック、マーケットカレンダー管理、ファクター計算、ニュースの NLP スコアリング、監査ログ（トレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- 環境・設定管理
  - .env / .env.local 自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 必須設定を明示的に検証

- データパイプライン（ETL）
  - J-Quants API からの差分取得（株価・財務・マーケットカレンダー）
  - 冪等保存（DuckDB への INSERT ... ON CONFLICT DO UPDATE）
  - 品質チェック（欠損・重複・スパイク・日付不整合検出）
  - 日次 ETL エントリ（run_daily_etl）

- データ管理ユーティリティ
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar 更新ジョブ）
  - 統計ユーティリティ（Zスコア正規化 等）
  - ニュース収集（RSS -> raw_news、SSRF/サイズ制限/トラッキング除去 等）

- 研究用ツール
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算・IC（Information Coefficient）計算
  - ファクターの統計サマリー

- AI ベースの解析
  - ニュースのセンチメントスコアリング（OpenAI を使用、gpt-4o-mini）
  - 市場レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメントの合成）

- 監査・トレーサビリティ
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査DB 初期化関数（init_audit_db）

---

## 必須環境変数（主なもの）

プロジェクトは .env を利用して設定できます。必須の環境変数は実行する機能により異なります。代表的なもの:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（実行・注文連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知（必要な場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

オプション（デフォルトがあるもの）:

- KABU_API_BASE_URL — kabu API base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

自動 .env ロードの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）。

---

## 依存パッケージ（代表例）

ソース内の利用から推定される主要依存パッケージ:

- Python 3.9+（型注釈から 3.10 以降も想定される）
- duckdb
- openai
- defusedxml

インストールはプロジェクトの requirements.txt があればそれを使用してください。無い場合は最低限次を入れると動きます:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（実際のプロジェクトでは setup.py / pyproject.toml / requirements.txt を参照して依存を確定してください）

---

## セットアップ手順（簡易）

1. レポジトリをクローン

```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境作成・有効化・依存インストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt    # ある場合
# または最低限:
pip install duckdb openai defusedxml
```

3. .env を作成（.env.example を参照）

必須項目を設定してください（例）:

```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
KABU_API_PASSWORD=...
```

4. DuckDB データベースディレクトリ作成（必要なら）

デフォルトでは data/ 配下を使用する設定になっています。なければ作成しておくと良いです。

```bash
mkdir -p data
```

---

## 使い方（主要な API 例）

下記はライブラリを Python スクリプトや REPL から利用する際の代表的な例です。

- 設定の利用

```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続（ETL / その他）

```python
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- 監査DBを初期化する（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

- ニュース NLP（ai_score）を計算して ai_scores テーブルへ書き込む

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API key: 環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（regime score）を計算して market_regime テーブルへ書き込む

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算（例: momentum）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# mom は dict のリスト: [{'date': ..., 'code': 'XXXX', 'mom_1m': ..., ...}, ...]
```

---

## 注意点と設計上のポリシー（重要な挙動）

- Look-ahead バイアス回避
  - 多くの関数は datetime.today() / date.today() を内部で参照せず、引数で与えた target_date に基づいて処理します。バックテスト利用時は target_date を明示してください。

- 自動 .env ロード
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env/.env.local を自動で読み込みます。これを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI API の扱い
  - news_nlp / regime_detector は OpenAI を使用します。API 呼び出し失敗時にはフェイルセーフの挙動（スコア 0 を採用、あるいはスキップ）で継続しますが、API キーは必須です（引数または OPENAI_API_KEY）。

- J-Quants API
  - jquants_client にはレートリミッタ、再試行、401 リフレッシュロジックがあります。JQUANTS_REFRESH_TOKEN を必ず設定してください。

---

## ディレクトリ構成（ソース概観）

以下は主要ファイル・モジュールの一覧（src/kabusys 以下）。実際のリポジトリに合わせて調整してください。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ化されている想定: 実ファイルはプロジェクト参照)
  - strategy/ (戦略層、実装に応じて存在)
  - execution/ (約定・発注関連、実装に応じて存在)

（README にある構成はコードベースの一部を抜粋しています。プロジェクトルートのツリーを確認してください）

---

## よくある操作例（ショートカット）

- .env の自動読み込みを無効にして環境を手動で注入（テスト時）:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
export OPENAI_API_KEY="sk-..."
python -c "from kabusys.config import settings; print(settings.log_level)"
```

- DuckDB を使った簡易クエリ

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
rows = conn.execute("SELECT COUNT(*) FROM raw_prices").fetchall()
print(rows)
```

---

## 参考・トラブルシュート

- OpenAI 呼び出しで JSON 解析に失敗することがあるため、news_nlp/regime_detector はパース失敗時にログを出しフォールバックします。ログをチェックしてください。
- J-Quants の 401 は自動でリフレッシュする設計ですが、リフレッシュトークンが無効な場合はエラーになります。JQUANTS_REFRESH_TOKEN を確認してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン特性に対応するため、コード上でも空チェックを行っています。

---

この README はソースコードのコメント・ドキュメントに基づく概要です。各モジュールの詳細な API 仕様や追加ユーティリティはソースコード内の docstring を参照してください。必要であれば、特定機能の使い方やサンプルを追加しますので教えてください。