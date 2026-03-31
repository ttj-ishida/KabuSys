# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
市場データの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです：

- J-Quants API などからの株価・財務・カレンダーデータの差分取得（ETL）
- RSS ニュースの収集と銘柄ごとの LLM ベースのセンチメント付与（gpt-4o-mini を想定）
- ETF（1321）やニュースを組み合わせた市場レジーム判定
- ファクター（モメンタム/バリュー/ボラティリティ等）計算と研究用ユーティリティ
- DuckDB を用いたデータ格納・品質チェック・監査ログ管理

設計上の特徴：
- ルックアヘッドバイアス対策（date.today() を直接参照しない等）
- API 呼び出しはリトライ・バックオフ等の堅牢な実装
- DuckDB での冪等保存（ON CONFLICT）や監査テーブルによるトレーサビリティ
- 外部依存は最小限（openai, duckdb, defusedxml など）

---

## 主な機能一覧

- data/etl: 日次 ETL パイプライン（prices, financials, calendar）
- data/jquants_client: J-Quants API からの取得・保存ユーティリティ（レート制御・リトライ・トークン管理）
- data/news_collector: RSS フィード収集・前処理・raw_news への保存
- data/quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data/audit: 監査ログスキーマ初期化と監査 DB ユーティリティ
- ai/news_nlp: ニュースを LLM に投げて銘柄別センチメント（ai_scores）を生成
- ai/regime_detector: ETF の MA乖離 と マクロニュースセンチメントを合成した市場レジーム判定
- research: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、Z スコア正規化等
- config: .env 自動読み込み・設定管理（settings オブジェクト）

---

## 必要条件（依存ライブラリ）

最低限必要なパッケージ（抜粋）：

- Python 3.10+
- duckdb
- openai
- defusedxml

プロジェクト用途に応じてさらに依存（例えば Slack 通知や SQLlite 等）がある場合があります。requirements.txt がある場合はそれを使用してください。

例インストール：
```bash
python -m pip install duckdb openai defusedxml
# 開発モードでプロジェクトを編集可能にインストールする場合
pip install -e .
```

---

## 環境変数 / .env

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 用パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

.env のテンプレート例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定はコード上の `from kabusys.config import settings` でアクセスできます（例: settings.jquants_refresh_token）。

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repository-url>
cd <repo>
```

2. 仮想環境作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate   # Windows
```

3. 依存ライブラリをインストール
```bash
pip install -r requirements.txt  # もしあれば
# または個別インストール
pip install duckdb openai defusedxml
```

4. .env を作成（プロジェクトルート）
- 上記テンプレートを参考に必要な値を設定します。

5. DuckDB 等の初期化（任意）
- 監査ログ専用 DB を初期化する場合は Python から実行（下記参照）。

---

## 使い方（主要 API のサンプル）

以下は Python REPL またはスクリプトでの利用例です。全ての関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り）を受け取ります。

- DuckDB 接続の作成例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

### 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn: duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

### ニュースの NLP スコアを付与して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、OPENAI_API_KEY 環境変数を設定してください
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {count}")
```

### 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

### 監査ログ（audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_db

# ファイルベース DB を作成してスキーマを生成
conn_audit = init_audit_db("data/audit.duckdb")
```

### 研究用ユーティリティ（ファクター計算）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value

momentum_records = calc_momentum(conn, target_date=date(2026,3,20))
value_records = calc_value(conn, target_date=date(2026,3,20))
```

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下にモジュールを配置しています。主要なファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLP（LLM 呼び出し、ai_scores へ書込）
    - regime_detector.py — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - news_collector.py  — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー関連ユーティリティ
    - quality.py         — データ品質チェック
    - stats.py           — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py           — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/（LLM 系）
  - research/（解析系）

---

## 開発・運用上の注意

- 環境変数はセキュアに管理してください（API キー等）。
- OpenAI 呼び出しはトークンや料金が発生します。テスト時は api_key を渡すかモックしてください。news_nlp/regime_detector の内部 `_call_openai_api` はユニットテストで差し替え可能です。
- DuckDB の executemany に関する挙動（空リスト不可）に注意して実装されています。直接 SQL を書き換える際は互換性を保ってください。
- config.py はプロジェクトルートを `.git` または `pyproject.toml` から自動検出して `.env` を読み込みます。テストで自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ライセンス・貢献

（ここにプロジェクトのライセンスや貢献方法を記載してください）

---

この README はコードベース（src/kabusys）に基づいて生成しています。詳細な API や追加のユーティリティについては該当モジュールの docstring を参照してください。必要であればサンプルスクリプトや Docker 化、CI 例も作成できます。