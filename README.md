# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ群です。  
J-Quants や RSS からのデータ収集、ETL、データ品質チェック、ニュースの LLM ベースセンチメント分析、マーケットレジーム判定、監査ログ（トレーサビリティ）などを提供します。

---

## 主な特徴

- J-Quants API との安全な連携（認証自動リフレッシュ、レート制御、リトライ）
- DuckDB を用いたローカルデータストア（冪等保存 / ON CONFLICT）
- ETL パイプライン（株価日足 / 財務 / 市場カレンダー / 品質チェック）
- ニュース収集（RSS）と前処理（SSRF対策 / トラッキング除去）
- ニュースの LLM ベースセンチメント分析（gpt-4o-mini など、JSON Mode 対応）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの組合せ）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、正規化）

---

## 必須要件

- Python 3.10+
- インストール必須パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml

例:
```bash
python -m pip install "duckdb>=0.7" openai defusedxml
```

（プロジェクトルートに pyproject.toml / requirements.txt がある場合はそちらを使ってください）

---

## 環境変数（.env）

重要な設定は環境変数で管理します。プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただしテスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主なキー:
- JQUANTS_REFRESH_TOKEN - J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY - OpenAI API キー（score_news / regime_detector で使用）
- KABU_API_PASSWORD - kabuステーション API パスワード
- KABU_API_BASE_URL - kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack チャンネル ID
- DUCKDB_PATH - DuckDB の保存パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 実行環境 (development / paper_trading / live)
- LOG_LEVEL - ログレベル (DEBUG / INFO / ...)

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `kabusys.config.settings` から参照できます（プロパティベース）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. Python 仮想環境の作成 & 有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt    # あれば
   # ない場合:
   pip install duckdb openai defusedxml
   ```
4. パッケージをローカルインストール（編集しながら使う場合）
   ```bash
   pip install -e .
   ```
5. `.env` を用意（上記を参照）。自動読み込みは `kabusys.config` によってプロジェクトルートの `.env` / `.env.local` をロードします。

---

## 使い方（API 例）

以下はライブラリの主要操作を行う簡単なサンプルです。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai スコア）を日次で実行:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されているか、api_key を直接渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書込んだ銘柄数: {num_written}")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- 設定参照例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

注意点:
- LLM を使う関数（score_news / score_regime）は API キーを引数で受け取れますが、引数省略時は環境変数 `OPENAI_API_KEY` を参照します。
- ETL や保存処理は冪等（ON CONFLICT）を前提としています。
- 内部で datetime.today() / date.today() を直接参照しない設計が多く、テスト／バックテストでの変動を避けています。

---

## よく使うモジュール（概要）

- kabusys.config
  - 環境変数読み込み・検証（.env 自動ロード、Settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアントと DuckDB 保存関数
  - pipeline: ETL 実行（run_daily_etl 等）
  - calendar_management: JPX カレンダー管理 / 営業日判定
  - news_collector: RSS 取得とテキスト前処理（SSRF対策）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化
  - stats: z-score 正規化など
- kabusys.ai
  - news_nlp: ニュースを集約し LLM でセンチメントを生成して ai_scores に保存
  - regime_detector: ETF 1321 の MA とマクロニュースを組合せた市場レジーム判定
- kabusys.research
  - factor_research: Momentum / Volatility / Value ファクター計算
  - feature_exploration: 将来リターン・IC・サマリー等

---

## ディレクトリ構成（抜粋）

プロジェクト内部の主要ファイルと役割（src/kabusys 以下）:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数 / Settings
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - other helpers...
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
  - その他研究用ユーティリティ

（README 内では主要モジュールのみ列挙しています。実際のファイル一覧はプロジェクトを参照してください。）

---

## ログ・デバッグ

- log レベルは環境変数 `LOG_LEVEL`（デフォルト INFO）で制御します。
- 各モジュールは標準的な logging を使用しており、詳細なデバッグ情報は DEBUG レベルで出力されます。

---

## テスト・開発

- 設計上、外部 API 呼び出し箇所（OpenAI / J-Quants / HTTP）は差し替えやモックが容易な実装にしています。
- 単体テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動 .env 読み込みを無効にすると安定化します。

---

## 注意事項 / ベストプラクティス

- OpenAI や J-Quants の API キーは安全に管理してください。CI に平文で置かないこと。
- 本ライブラリには実行・発注機能の雛形が含まれる可能性があります。実運用（特に live モード）に移す際は十分なレビューとテストを行ってください（KABUSYS_ENV=live の挙動確認等）。
- DuckDB ファイルはバイナリで保持されるため、バックアップや排他アクセスに注意してください。

---

必要であれば、README に CLI の使い方例や CI / テストの書き方、より詳細な API リファレンス（関数引数/戻り値の例）を追加します。どの部分を詳しく記載しましょうか？