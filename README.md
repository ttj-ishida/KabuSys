# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants 経由の市場データ取得）、ニュース収集・NLP（OpenAI を利用した銘柄センチメント算出）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買・研究プラットフォーム向けに設計されたモジュール群です。主な目的は以下です。

- J-Quants API からのデータ取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメント（市場レジーム）評価
- 研究用のファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック・市場カレンダー管理
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）スキーマの初期化ユーティリティ

設計上の特徴として、ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない）、API リトライ・バックオフ、ETL の冪等性、安全対策（SSRF、XML データの防御）などを重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの日次株価（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得
  - DuckDB への冪等保存（ON CONFLICT を利用）
  - run_daily_etl を使った日次パイプライン実行（カレンダー→日足→財務→品質チェック）

- ニュース収集 / NLP
  - RSS フィードから記事収集（URL 正規化、トラッキングパラメータ除去、SSRF 対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント score_news
  - マクロニュースと ETF（1321）MA 乖離から市場レジームを判定する score_regime

- 研究（Research）
  - calc_momentum, calc_value, calc_volatility：ファクター計算
  - calc_forward_returns, calc_ic, factor_summary：特徴量評価・IC 計算
  - zscore_normalize：クロスセクション正規化ユーティリティ

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検出（run_all_checks）

- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注の冪等化を支援する order_request_id

---

## 必要条件 / 依存ライブラリ（例）

- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
- その他（利用機能に応じて）
  - urllib 等標準ライブラリを使用
  - (Slack 通知等を実装する場合は slack_sdk 等が必要になる可能性があります)

インストール例（develop mode）:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# またはパッケージとしてセットアップされていれば:
# python -m pip install -e .
```

---

## 環境変数 / 設定

KabuSys は .env / 環境変数から設定を読み込みます（自動でプロジェクトルートの .env と .env.local を読み込みます）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: Slack Channel ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等の SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")（省略時: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（省略時: INFO）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）

.env ファイルのパースはシェル形式をサポートしており、クォートやコメントの処理に配慮しています。

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -U pip
   python -m pip install duckdb openai defusedxml
   # 必要に応じて追加ライブラリを導入
   ```

3. 環境変数を準備（.env を作成）
   例: `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB（データベース）用ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な API の例）

下記は簡単な利用例です。実際にはロガー設定や例外ハンドリングを追加してください。

- DuckDB 接続と日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path を返します
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を用いたニューススコアリング（銘柄別）
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定（または第3引数で api_key を渡す）
count = score_news(conn, target_date=date(2026,3,20))
print(f"写込銘柄数: {count}")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査用 DB 初期化（監査スキーマの作成）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # transactional により安全に初期化されます
```

- RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## よく使うモジュール位置

- kabusys.config
  - 環境変数設定管理（Settings クラス）
- kabusys.data
  - jquants_client.py: J-Quants API クライアント & DuckDB 保存ユーティリティ
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS 収集・前処理
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - quality.py: データ品質チェック
  - audit.py: 監査ログスキーマ初期化
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.py: 銘柄ニュースのセンチメント算出（score_news）
  - regime_detector.py: 市場レジーム判定（score_regime）
- kabusys.research
  - factor_research.py: ファクター計算（calc_momentum, calc_value, calc_volatility）
  - feature_exploration.py: 将来リターン・IC・統計サマリー等

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - audit DB 初期化ユーティリティ等
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（各ファイルは README の「主な機能一覧」節で触れた機能群を実装しています）

---

## 実運用上の注意点

- OpenAI API 使用時はコストとレート制限に注意してください。score_news はバッチ処理（_BATCH_SIZE）で API に送る設計です。
- J-Quants API にはレート制限があり、jquants_client は内部でレート制御とリトライを行います。ID トークンの自動リフレッシュにも対応しています。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、コード内で空チェックをしてから実行しています。運用中の DuckDB バージョンに注意してください。
- ETL / AI モジュールは Look-ahead バイアス防止のため設計された挙動を持ちます。バックテスト実行時は ETL の取得タイミングに注意して下さい。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト時に自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

必要に応じて README を拡張します（例: CLI や Docker 化、CI 設定、サンプル .env.example、より詳細な API リファレンス）。どの情報を追加したいか教えてください。