# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants）→ データ品質チェック → 研究（ファクター計算） → AI ニュース分析 → 監査ログ（発注トレース）までをカバーします。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化など）
- ニュース収集（RSS）と LLM を用いた銘柄別 / マクロセンチメントスコアリング
- 市場レジーム判定（ETF MA とマクロ LLM スコアの合成）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 環境変数/設定管理（.env 自動読み込みを含む）

設計方針として、バックテストでのルックアヘッドバイアスを避ける（datetime.now() を無制限に参照しない）こと、DuckDB を中心に SQL＋軽量 Python で実装し外部依存を最小化することを重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・レート制御・保存関数）
  - カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS の安全な取得・正規化・raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（監査テーブル DDL / インデックス、init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化など）
- research/
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- ai/
  - news_nlp: ニュースをまとめて LLM（gpt-4o-mini）に投げ、銘柄別スコアを ai_scores に書き込む
  - regime_detector: ETF（1321）200日MA乖離とマクロ LLM スコアを合成して market_regime に保存
- config: .env 自動ロード、必須環境変数チェック、settings オブジェクト
- audit: 発注〜約定の監査テーブル作成 / 初期化ユーティリティ

---

## 前提 / 必要環境

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード, OpenAI API）

（このリポジトリに requirements.txt が無い場合は上記パッケージをインストールしてください）

例:
```bash
python -m pip install "duckdb>=0.8" openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   python -m pip install -e .   # パッケージとして使う場合（setup.py/pyproject がある前提）
   # または必要なライブラリを個別に pip install
   ```
4. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）
   - 自動ロードは config モジュールで .git または pyproject.toml を探索し有効化されます。
   - 自動ロードを無効化するには環境変数を設定:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector）
   - オプション / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

   簡易 .env.example:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な利用例）

以下はライブラリをインポートして使う最小例です。すべて duckdb 接続を渡して動かします。

- ETL（1日分の ETL を実行）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- J-Quants から株価を直接フェッチして保存（ETL ヘルパーの内部で使われる）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,19))
saved = save_daily_quotes(conn, records)
```

- ニュースのセンチメントスコアを作成（AI を使う）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key=None -> env OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

- 市場レジーム判定（regime_detector）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # :memory: でインメモリ可
```

- データ品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点:
- OpenAI への呼び出しは gpt-4o-mini を想定（response_format=json_object を利用）。API レート・エラー時のリトライやフェイルセーフが組まれていますが、API キーは必須です。
- run_daily_etl 等は内部でカレンダー調整やバックフィルを行います（Look-ahead バイアスに注意）。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (必須 for AI functions)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須 if Slack integration used)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

環境変数はプロジェクトルートの .env → .env.local の順に読み込まれます（OS 環境変数が優先）。config.Settings で必須チェックが行われます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP スコアリング（ai_scores 書込）
    - regime_detector.py     -- 市場レジーム判定（market_regime 書込）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch / save）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult の再エクスポート
    - calendar_management.py -- 市場カレンダー管理
    - news_collector.py      -- RSS 収集・正規化・保存
    - quality.py             -- データ品質チェック
    - stats.py               -- 汎用統計ユーティリティ（zscore）
    - audit.py               -- 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py     -- Momentum / Value / Volatility 等
    - feature_exploration.py -- forward returns / IC / summaries

（上記はこの README に含まれる代表的なファイルの一覧です）

---

## テスト / 開発時のヒント

- 自動 .env ロードはプロジェクトルートの .git または pyproject.toml を起点に探します。ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自分で環境を制御すると良いです。
- OpenAI 呼び出しは内部で _call_openai_api をラップしているため、テスト時は unittest.mock.patch で差し替えて応答を固定できます。
- news_collector の HTTP 関連は _urlopen などをモックして外部アクセスを切り離せます。
- DuckDB を使った関数はインメモリ DB (":memory:") でも動作するため、テストが容易です。

---

## ライセンス / 貢献

（プロジェクトのライセンスやコントリビュート方法をここに記載してください）

---

以上が KabuSys の概要と導入・利用手順のサマリです。README に追加して欲しい具体的なコマンドやサンプル（例: systemd / Airflow での運用例、Slack 通知の導入等）があれば教えてください。