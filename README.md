# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のための Python ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携し、データ取得（ETL）、ニュース NLP、ファクター算出、監査ログ、マーケットカレンダー管理などを提供します。

主な設計方針としては「ルックアヘッドバイアスの回避」「DuckDB を用いた冪等保存」「外部 API のレート制御とリトライ」「安全対策（SSRF, XML 脆弱性対策等）」が採られています。

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価（daily quotes）・財務データ・市場カレンダーの差分取得（ページネーション対応）
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の結果を集約する ETLResult データ構造

- ニュース収集・NLP
  - RSS フィード収集（トラッキングパラメータ除去、SSRF 対策、gzip 制限）
  - raw_news / news_symbols 連携による銘柄ごとの記事集約
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュースの LLM 評価と ETF（1321）200 日 MA を合成した市場レジーム判定（score_regime）

- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- データユーティリティ
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - 監査ログ（signal_events, order_requests, executions）スキーマ初期化ユーティリティ
  - レートリミッタ、HTTP リトライ・トークンリフレッシュ処理など

- 設定管理
  - 環境変数 / .env ファイル自動読み込み（プロジェクトルート検出）
  - 必須設定のプロパティ提供（settings オブジェクト）

---

## 必要環境 / 依存

- Python 3.10+
  - 型ヒント（X | Y 形式）を使用しているため 3.10 以上を想定しています。
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他、標準ライブラリのみで実装されている部分も多いです）

インストールはプロジェクトの packaging に依存しますが、ローカルで開発する場合の例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# またはプロジェクトが配布用の requirements.txt を持つ場合:
# pip install -r requirements.txt
```

---

## 環境変数（主なもの）

KabuSys は環境変数から設定を読み込みます。主に以下を設定してください（必要に応じて .env を用意）。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（ETL で使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード

- KABU_API_BASE_URL (任意)  
  kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン

- SLACK_CHANNEL_ID (必須)  
  Slack 送信先チャンネル ID

- OPENAI_API_KEY (必須 for AI)  
  OpenAI API キー（ニュース NLP / レジーム判定で利用）

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH (任意)  
  監視用 SQLite パス（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)  
  環境: development / paper_trading / live （デフォルト: development）

- LOG_LEVEL (任意)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)  
  自動 .env ロードを無効化する場合に 1 を設定

自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に .env → .env.local の順で行われます。.env.local は .env の上書き（優先）になります。

例 (.env.example):

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（duckdb / openai / defusedxml 等）
4. プロジェクトルートに .env（または .env.local）を作成して環境変数を設定
5. DuckDB を使う場合は必要に応じて DB ファイルの親ディレクトリを作成

例:

```bash
git clone <repo_url>
cd repo
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
cp .env.example .env
# .env を編集して必要なキーを設定
```

※ 自動で .env を読み込む動作は、テストなどで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要 API の例）

以下は代表的な呼び出し例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）を設定してください。

- DuckDB 接続例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）:

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が使われます
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース NLP（指定日のニューススコアリング）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 とマクロニュースの合成）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込みされます
```

- 監査ログ DB の初期化（監査専用 DB を作る場合）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- ファクター計算（研究用途）:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- OpenAI 呼び出しを行う関数（score_news / score_regime）は API キーを引数に渡すか、環境変数 OPENAI_API_KEY を設定する必要があります。
- DuckDB のテーブルスキーマは本プロジェクト外で作成されている前提です（ETL / save_* 系は既存テーブルへ冪等に挿入します）。初期スキーマ作成のユーティリティがある場合はそちらを先に実行してください（例: audit.init_audit_schema 等）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

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

主なサブパッケージの役割:
- kabusys.config: 環境変数・設定管理（.env 自動読み込み、必須設定取得）
- kabusys.data: データ ETL / カレンダー管理 / J-Quants クライアント / ニュース収集 / 品質チェック / 監査ログ
- kabusys.ai: ニュース NLP と市場レジーム判定（OpenAI 連携）
- kabusys.research: ファクター計算・解析補助

---

## 設計上の重要な注意点

- ルックアヘッドバイアス回避
  - 日付比較やデータ取得は target_date 未満 / 以前の制約を厳密に適用しており、内部で datetime.today() を参照しない関数が多くあります（バックテストやデータ更新の一貫性を保つため）。

- 冪等性
  - DuckDB への保存は ON CONFLICT を使った冪等更新を行います。ETL は差分取得＋バックフィルを採用。

- API 安全性
  - J-Quants クライアントはレートリミット管理とリトライ、401 リフレッシュ処理を実装しています。
  - RSS 収集は SSRF 対策、gzip 制限、defusedxml による XML 攻撃対策を実施しています。

- フェイルセーフ
  - LLM 呼び出し（OpenAI）が失敗した場合、スコアは安全側（0.0）にフォールバックする設計箇所があります。ETL 各ステップは独立して例外を捕捉し、可能な限り他処理を継続します。

---

## 開発 / テストに関するヒント

- 自動 .env 読み込みを無効にする:
  - テスト中に環境を汚したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- OpenAI 呼び出しのモック:
  - tests では `kabusys.ai.news_nlp._call_openai_api` や `kabusys.ai.regime_detector._call_openai_api` を patch して外部 API 呼び出しをモックできます。

- DuckDB の互換性:
  - 一部の実装は DuckDB のバージョン依存（executemany の空リストなど）に注意しているため、本番環境と開発環境で DuckDB バージョンを揃えてください。

---

必要な追加情報（例: schema 定義、requirements.txt、運用手順、CI 設定など）があれば、README を拡張して運用ガイドや API リファレンス、サンプルワークフロー（ETL cron、監視アラート、Slack 通知）を追加できます。どの情報を優先して追記しますか？