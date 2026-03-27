# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォームと研究・シグナル生成・監査ログ基盤を備えた自動売買システムのコアライブラリです。本リポジトリは ETL、ニュースセンチメント（LLM）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー/約定トレース）などを提供します。

主な設計方針
- バックテストでのルックアヘッドバイアス回避を重視（date/timestamp の扱いに注意）
- DuckDB を中心としたローカルデータレイヤ
- J-Quants / OpenAI 等の外部 API 呼び出しはリトライ・レート制御・フォールバック実装あり
- ETL / 保存処理は冪等（ON CONFLICT / upsert）で安全
- テスト容易性のため API キー注入やモック差し替えが可能

---

## 機能一覧

- データ取得・ETL
  - J-Quants クライアント（株価 / 財務 / JPX カレンダー取得）: kabusys.data.jquants_client
  - 日次 ETL パイプライン: kabusys.data.pipeline.run_daily_etl
  - カレンダー更新ジョブ: kabusys.data.calendar_management.calendar_update_job

- ニュース収集・NLP（OpenAI 経由）
  - RSS 収集・前処理・raw_news 保存: kabusys.data.news_collector
  - ニュースセンチメント集計（銘柄ごと）: kabusys.ai.news_nlp.score_news
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定: kabusys.ai.regime_detector.score_regime

- 研究 / ファクター
  - Momentum / Value / Volatility / Liquidity 等のファクター計算: kabusys.research.factor_research
  - 将来リターン計算・IC/統計サマリ: kabusys.research.feature_exploration
  - Zスコア正規化ユーティリティ: kabusys.data.stats.zscore_normalize

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック: kabusys.data.quality

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義・初期化とヘルパー: kabusys.data.audit

- 設定管理
  - .env / 環境変数読み込み、自動ロード/保護された上書き: kabusys.config.settings

---

## 前提・依存（例）

この README はライブラリの使い方を説明します。実行環境に応じて必要な依存をインストールしてください。主要な外部パッケージ例:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他（ネットワークアクセス用標準ライブラリを使用）

pip での例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発時: ローカルパッケージとしてインストール
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <this-repo-url>
cd <repo>
```

2. 仮想環境作成・依存インストール（上記参照）

3. 環境変数 / .env 設定  
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただしテスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。  
   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY（score_news / regime_detector を使う場合）

   任意 / デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化

   .env.example（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベースディレクトリの作成（必要に応じて）
```bash
mkdir -p data
```

---

## 使い方（主要な操作例）

以下は Python スクリプトや対話環境での簡単な例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # または ":memory:"
```

- 日次 ETL を実行する（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む（OpenAI APIキーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか OPENAI_API_KEY 環境変数を設定
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"wrote scores for {count} codes")
```

- 市場レジーム判定を実行して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査ログ用 DB の初期化（独立した監査DBを作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

- カレンダー更新ジョブ（J-Quants経由でmarket_calendarを更新）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

- 品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意:
- OpenAI を使う処理（score_news, score_regime）は API 呼び出しに失敗するとフェイルセーフでスコアを 0 にする、あるいはスキップする実装です（システムが停止しないよう設計）。
- ETL・保存処理は基本的に冪等（再実行可）です。ただしバックテスト用途では取得時刻や利用順序に注意してください。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義（data, strategy, execution, monitoring をエクスポート）
  - config.py — 環境変数／.env 自動読み込み、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI）と ai_scores 書き込みのロジック
    - regime_detector.py — ETF MA200 とマクロニュースでレジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存 / レート制御 / リトライ）
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py — RSS 収集・前処理・raw_news 保存ロジック（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - stats.py — z-score 正規化ユーティリティ
    - quality.py — データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログテーブル初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/（上記）
  - その他:
    - strategy, execution, monitoring パッケージ（README では詳細省略。実装に応じて拡張）

---

## 開発・テストに関するメモ

- 環境設定の自動読み込みはプロジェクトルート（.git または pyproject.toml を親ディレクトリで検索）を基に行われます。テストで自動読み込みを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI 呼び出しやネットワーク処理はモジュール内で差し替え可能な小さなラッパー関数（例: _call_openai_api, _urlopen）を用意してあり、unit-test でモック可能です。
- DuckDB に対する executemany の扱いやトランザクションについてはコード内に互換性に対する注記があります。DuckDB のバージョン差に注意してください。

---

## ライセンス・貢献

この README はコードベースの簡易ドキュメントです。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、各モジュールごとの詳細な API 仕様（関数引数・戻り値・例外）や、サンプルワークフロー（ETL → ニュース収集 → スコアリング → シグナル生成 → 発注ログ）を別ドキュメントとして作成します。どの部分を詳述したいか教えてください。