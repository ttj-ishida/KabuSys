# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ ETL、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー管理、J-Quants / kabu ステーション / OpenAI 連携などの機能群を提供します。

---

## 主な特徴 (Features)

- データ取得・ETL
  - J-Quants API から株価（日足）、財務、マーケットカレンダー等をページネーション対応で取得
  - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存
  - 差分取得・バックフィル・品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集 / NLP
  - RSS フィードから安全にニュースを収集し raw_news に保存（SSRF / XML 爆弾対策あり）
  - OpenAI （gpt-4o-mini）を用いたニュースセンチメント評価（銘柄ごとの ai_score 生成）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント合成）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクターの統計サマリー
  - Zスコア正規化ユーティリティ

- 監査・発注トレーサビリティ
  - signal_events / order_requests / executions といった監査テーブルを DuckDB に冪等作成
  - order_request_id を冪等キーとして二重発注防止

- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境に応じた設定（development / paper_trading / live）やログレベル制御

---

## 必要条件 (Requirements)

- Python 3.10+
- 推奨パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトで利用する機能に応じて他の依存が必要になる可能性があります）

例（最低限インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

またはパッケージ化されていれば:
```
pip install -e .
```

---

## 環境変数 / .env 設定

このパッケージは .env ファイルまたは環境変数から設定値を読み込みます（自動ロードの優先順は OS 環境変数 > .env.local > .env）。  
自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（最低限必要なもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C01XXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順 (Quickstart)

1. リポジトリをクローンして仮想環境を作成
```
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
```

2. 必要パッケージをインストール（プロジェクトの requirements.txt があればそれを使う）
```
pip install duckdb openai defusedxml
# その他、必要なライブラリがあれば追加でインストール
```

3. .env を用意（上記参照）  
   プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を置くと自動で読み込まれます。

4. DuckDB データベースの初期化（監査 DB など）:
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db
import duckdb
from pathlib import Path

db_path = settings.duckdb_path  # Path オブジェクト
conn = init_audit_db(db_path)   # 監査用 DB を作る場合
# または
conn = duckdb.connect(str(db_path))
# 必要なスキーマは別モジュールから初期化することも可能
```

---

## 使い方（代表的な API）

以下は代表的な呼び出し例です。多くの関数は duckdb.DuckDBPyConnection を引数に取ります。

- ETL 日次パイプライン実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄ごと）スコアリング
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定しておくか、第3引数にキーを渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査テーブルの初期化（既存 DB 接続に対して）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

- Zスコア正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
```

---

## 注意点・設計方針（抜粋）

- ルックアヘッドバイアス対策:
  - 日付判定やスコアリングの多くの関数は内部で datetime.today() / date.today() を直接参照しない設計です。バックテスト時には必ず明示的な target_date を渡してください。
  - データ取得は target_date を基準に「未満 / 排他」条件を使う等、未来情報漏洩を防いでいます。

- 冪等性:
  - ETL の保存処理は基本的に ON CONFLICT DO UPDATE 等で冪等性を担保します。

- フェイルセーフ:
  - OpenAI/API の呼び出し失敗時はゼロスコアやスキップで継続する実装が多く、完全停止させない設計です（ログは出力されます）。

- セキュリティ:
  - RSS 取得には SSRF 対策、XML 関連の攻撃対策（defusedxml）、受信サイズ制限を実装しています。
  - J-Quants API 呼び出しはレートリミットを守る実装が組み込まれています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

```
src/kabusys/
├─ __init__.py
├─ config.py                      # 環境変数・設定管理
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py                 # ニュースNLP（OpenAI連携）
│  └─ regime_detector.py          # 市場レジーム判定
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py           # J-Quants API クライアント & DuckDB 保存
│  ├─ pipeline.py                 # ETL パイプライン（run_daily_etl など）
│  ├─ news_collector.py           # RSS 収集
│  ├─ quality.py                  # 品質チェック
│  ├─ calendar_management.py      # マーケットカレンダー管理
│  ├─ audit.py                    # 監査ログ初期化 / init_audit_db
│  ├─ stats.py                    # 統計ユーティリティ（zscore）
│  └─ pipeline.py                 # ETLResult 等
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py          # Momentum/Value/Volatility 計算
│  └─ feature_exploration.py      # 将来リターン / IC / 統計サマリー
└─ research/...
```

（実際のリポジトリにはさらにモジュールやテスト、ドキュメントが存在する場合があります）

---

## よくある質問 (FAQ)

Q: 環境変数を .env 以外で指定したい  
A: OS の環境変数を優先します。自動 .env 読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

Q: OpenAI のレスポンスが不正な場合はどうなる？  
A: news_nlp / regime_detector 共にレスポンスのパースや API エラー発生時はフォールバック（スコア 0.0、あるいは該当銘柄スキップ）して処理を継続します。ログに警告が残ります。

Q: DuckDB のスキーマはどこで定義されている？  
A: 各データ保存関数（例: save_daily_quotes 等）は既存のテーブルを前提に動作します。初回利用時は別途スキーマ初期化処理（プロジェクト内のスキーマ定義スクリプト）を実行してください（リポジトリに schema 初期化用モジュールがある場合はそちらを使用）。

---

もし README の内容に追加したい「導入事例」「テスト実行方法」「CI 設定例」などの要望があれば教えてください。必要に応じてサンプル .env.example や初期スキーマ SQL 断片も作成します。