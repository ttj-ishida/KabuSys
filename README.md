# KabuSys

日本株自動売買 / データプラットフォーム用ライブラリのリファレンス実装です。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアントなどを含むモジュール群を提供します。

> 注意: このリポジトリは研究/開発目的のコードベースです。実運用（特に実口座での自動売買）へ適用する際は、追加のリスク管理・テストが必要です。

## プロジェクト概要
- データ収集（J-Quants API、RSSニュース）
- ETL（差分取得、保存、品質チェック）
- ニュースのNLP（OpenAIを用いた銘柄単位センチメント）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算）
- 監査ログ（シグナル→発注→約定のトレース用 DuckDB スキーマ）

主要な設計方針：
- ルックアヘッドバイアスに配慮（内部で date.today() 等に依存しない設計）
- DuckDB によるローカルデータ保管・クエリ
- API 呼び出しに対するリトライ/バックオフ・レート制御
- 冪等（idempotent）保存ロジックを重視

---

## 主な機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（prices, financials, market calendar）
  - RSS ニュース収集（SSRF 対策、正規化、raw_news への保存）
  - ETL パイプライン（差分取得・backfill・品質チェック）
- データ品質管理
  - 欠損値・重複・スパイク・日付不整合の検出（quality モジュール）
- 研究用解析
  - Momentum / Volatility / Value ファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、要約統計（feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats）
- ニュース NLP / 市場レジーム
  - ニュースをまとめて OpenAI (gpt-4o-mini) に投げ、銘柄別スコアを ai_scores に保存（ai.news_nlp.score_news）
  - ETF（1321）200日MA乖離とマクロニュースを合成して市場レジームを決定（ai.regime_detector.score_regime）
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を初期化

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型表記 (`X | None`) を使用）
- ネットワーク接続（J-Quants / OpenAI を利用する場合）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   必要な主要パッケージ（例）:
   - duckdb
   - openai
   - defusedxml

   requirements.txt を作るか、手動でインストールしてください:
   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに packaging 設定があれば `pip install -e .` も可能）

4. 環境変数設定  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動ロードされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
   - KABU_API_PASSWORD = <kabuステーションAPIパスワード>
   - KABU_API_BASE_URL = http://localhost:18080/kabusapi  # 任意（デフォルト）
   - SLACK_BOT_TOKEN = <Slack Bot Token>
   - SLACK_CHANNEL_ID = <Slack Channel ID>
   - OPENAI_API_KEY = <OpenAI API Key>
   - DUCKDB_PATH = data/kabusys.duckdb  # 任意
   - SQLITE_PATH = data/monitoring.db   # 任意
   - KABUSYS_ENV = development | paper_trading | live
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

   例 (.env.example):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要なユースケース例）

以下は最小限のコード例です。実際の運用ではロギング設定や例外ハンドリングを追加してください。

- DuckDB 接続の作成（設定経由のパス使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（1 日分のデータを取得して品質チェックまで実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（OpenAI API キーは env か引数で指定）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))  # returns number of codes written
print("written:", written)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
```

- 監査ログ用 DB 初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions)が作成される
```

- 監査スキーマ（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数で明示的にキーを渡せます。環境変数 OPENAI_API_KEY が使われますが、テストや再現性確保のため直接渡すのが推奨される場合もあります。
- ETL の run_daily_etl は内部でカレンダーを取得し、対象日を営業日に調整します（_adjust_to_trading_day）。

---

## 主要モジュール・ディレクトリ構成

リポジトリの主要なファイル/モジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースNLPスコアリング（score_news）
    - regime_detector.py  # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   # J-Quants API クライアント（fetch/save）
    - pipeline.py         # ETL パイプライン（run_daily_etl 等）
    - etl.py              # ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py   # RSS ニュース収集
    - calendar_management.py  # 市場カレンダー管理（is_trading_day 等）
    - stats.py            # 統計ユーティリティ（zscore_normalize）
    - quality.py          # データ品質チェック
    - audit.py            # 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum/value/volatility）
    - feature_exploration.py  # 将来リターン / IC / summary 等

（上記は本 README 作成時点の主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 環境変数 / 設定一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（任意）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意): デフォルト data/monitoring.db
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

---

## テスト / モックについてのメモ
- OpenAI 呼び出しは内部でラップされており、ユニットテストでは各モジュール内の _call_openai_api を patch して差し替えられる設計です（例: unittest.mock.patch）。
- RSS フェッチは _urlopen をモックして外部依存を切り離せます。
- J-Quants クライアントは get_id_token の自動リフレッシュや RateLimiter を持つため、統合テストは注意して実行してください（API レート制限や認証が必要）。

---

## 運用上の注意・安全策
- 実口座での自動発注を行う前に、必ず十分なシミュレーション（paper_trading）とリスクテストを行ってください。
- API キーやトークンは安全に管理し、公開リポジトリに含めないでください。
- DuckDB のファイルパスはバックアップ・権限管理を考慮してください。
- ニュース由来のスコアは LLM の挙動やプロンプトに依存します。取り扱いには注意してください。

---

この README はコードベース（src/kabusys）から抽出した情報に基づいて作成しています。詳細実装やさらなる使用例は各モジュールの docstring を参照してください。必要であれば、インストール手順や CI / 開発フローのテンプレート、より詳しい運用ドキュメント（環境構築、DB マイグレーション、運用監視）も作成します。どの情報を優先して追加しますか？