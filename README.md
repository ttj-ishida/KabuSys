# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォーム・リサーチ・自動売買の基盤ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携して、データ取得（ETL）・品質チェック・ニュースセンチメント解析・ファクター計算・監査ログ管理・市場レジーム判定などを行えます。

主な設計方針:
- ルックアヘッドバイアスを防ぐ（date 引数ベース、datetime.today() を参照しない関数設計）
- DuckDB を中心としたローカルデータベースで完結
- 冪等性を重視（ETL / DB 保存は ON CONFLICT / DELETE→INSERT で上書き）
- 外部 API 呼び出しはリトライ / レート制御 / フェイルセーフを備える

---

## 機能一覧

- data
  - ETL パイプライン（J-Quants から株価・財務・カレンダーを差分取得 / 保存）
  - 市場カレンダー管理（営業日判定・next/prev 営業日取得）
  - ニュース収集（RSS 取得・前処理・raw_news への保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - J-Quants クライアント（認証・ページネーション・レート制御・保存ユーティリティ）
  - 統計ユーティリティ（Zスコア正規化）
  - 監査ログ初期化（signal/order/execution の監査テーブル）
- ai
  - ニュース NLP（OpenAI を使った銘柄ごとのセンチメント付与） — score_news
  - 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM センチメントを合成） — score_regime
- research
  - ファクター計算（Momentum / Value / Volatility）
  - 特徴量探索（将来リターン計算・IC・統計サマリー 等）

---

## 要件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, logging 等を使用

（プロジェクトに requirements.txt があればそちらを参照してください。上記はコード内で利用されている主要ライブラリです）

---

## 環境変数（主なもの）

自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（プロジェクトルートは .git または pyproject.toml を探索します）。テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用（本コードベースでは参照のみ）
- SLACK_CHANNEL_ID — Slack 通知先チャネルID

オプション・デフォルト:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値が設定されていれば無効化）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- KABUS_API_BASE_URL 等（kabu API 基本URLはデフォルトで `http://localhost:18080/kabusapi`）

.env の値は .env.example を参考に作成してください（プロジェクトには .env.example がある想定です）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux / macOS)
   - .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成して必要なキーを記述
     例:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

   自動読み込みはデフォルトで有効です。テストなどで無効にする場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベースディレクトリの用意
   - デフォルトでは `data/` に DuckDB ファイル等が保存されます。必要に応じて作成してください（コードは親ディレクトリを自動作成する箇所もあります）。

---

## 使い方（代表的な API と実行例）

以下は Python REPL / スクリプトからの呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（日次）の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア付与（AI）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究モジュール（ファクター計算）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

- 監査ログ（監査DB初期化）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026,3,20))
for issue in issues:
    print(issue)
```

注意点:
- ai モジュールは OpenAI に依存します。API キーを環境変数 `OPENAI_API_KEY` に設定するか、関数の api_key 引数で渡してください。
- J-Quants には認証（リフレッシュトークン → id_token）が必要です。`JQUANTS_REFRESH_TOKEN` を設定してください。
- ETL 関数は外部 API 呼び出し時にリトライやレート制御を行いますが、API 料金や制限に注意して運用してください。

---

## 簡単なワークフロー例

1. ETL を定期実行（cron / Airflow / 任意のジョブランナー）
   - run_daily_etl を毎営業日夜間に実行して DuckDB を更新

2. ニュース収集と NLP
   - RSS 収集ジョブで raw_news を貯め、翌朝 score_news を実行して ai_scores を更新

3. ファクター計算とシグナル生成
   - research モジュールで因子を計算し、戦略層でシグナル生成

4. 監査ログと注文
   - 生成したシグナルは audit.order_requests に記録してから外部ブローカーへ発注

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py (パッケージエントリ、__version__ = "0.1.0")
  - config.py (環境変数 / .env 自動ロード / Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP スコアリング: score_news)
    - regime_detector.py (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント + DuckDB 保存)
    - pipeline.py (ETL パイプライン / run_daily_etl 等)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (市場カレンダー / 営業日判定)
    - stats.py (zscore_normalize)
    - quality.py (データ品質チェック)
    - audit.py (監査ログの DDL / 初期化)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)

---

## テスト・開発上の注意

- 自動 .env 読み込みはプロジェクトルートの .git / pyproject.toml を基準に行います。テストで環境の影響を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ai モジュールの OpenAI 呼び出しはテストでパッチ可能（モジュール内の _call_openai_api を patch）です。
- news_collector などはネットワーク接続を行うため、単体テストでは外部呼び出しをモックしてください。

---

この README はコードベース内の docstring と設計方針をまとめたものです。詳細な API の振る舞いや DB スキーマ、運用手順については該当モジュール（kabusys/data, kabusys/ai, kabusys/research）の docstring を参照してください。