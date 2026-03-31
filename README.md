# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買用ライブラリ群です。  
ETL、データ品質チェック、ニュース収集＋LLMによるセンチメント集約、市場レジーム判定、監査ログ（オーダー追跡）など、自動売買に必要な基盤的処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の領域をカバーするモジュール群で構成されています。

- データ取得・ETL（J-Quants API 経由）と DuckDB への永続化
- 市場カレンダー管理（JPX）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と銘柄ごとの AI センチメントスコア生成
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算、IC・forward return 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 設定・環境変数管理（自動 .env 読み込み）

設計上の特徴:
- Look-ahead bias を避けるため、内部で現在時刻を乱用しない（外部から target_date を渡す方式）
- DuckDB を中心に SQL と純 Python で処理（外部解析ライブラリへの依存を最小化）
- API 呼び出しは堅牢なリトライ・レート制御を備える
- 各 ETL / 書き込みは冪等性（ON CONFLICT / DELETE→INSERT の保護）を考慮

---

## 主な機能一覧

- data.jquants_client: J-Quants からのデータ取得（株価日足 / 財務 / 市場カレンダー）と DuckDB 保存関数
- data.pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL（run_prices_etl 等）
- data.quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
- data.news_collector: RSS 取得・前処理・raw_news への保存用ユーティリティ
- ai.news_nlp: ニュースを銘柄ごとに集約し LLM でスコアを算出して ai_scores に保存（score_news）
- ai.regime_detector: ETF（1321）200日MA乖離とマクロニュース LLM スコアを合成して market_regime に保存（score_regime）
- research: ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリー
- data.calendar_management: カレンダー取得・営業日判定ユーティリティ（is_trading_day / next_trading_day / get_trading_days 等）
- data.audit: 監査ログテーブルの初期化・DB作成ユーティリティ（init_audit_schema / init_audit_db）
- config: 環境変数の読み込み（.env 自動ロード）と Settings クラス

---

## セットアップ手順

1. Python と依存パッケージのインストール（例: Python 3.10+ 推奨）

   必須依存（抜粋）:
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # このプロジェクトを開発モードでインストールする場合:
   pip install -e .
   ```

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

2. 環境変数 / .env を用意

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 用）
   - SLACK_BOT_TOKEN: Slack 通知に使う Bot Token
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API を使う場合（ai.score_news / score_regime など）

   その他:
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live, デフォルト development)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト INFO)

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

3. データベース初期化（監査ログ用など）

   監査ログ専用 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 以降 conn を渡して監査テーブルにアクセス可能
   ```

---

## 使い方（簡単な例）

Python スクリプト内での利用を想定した例をいくつか示します。

- DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（AI）を実行する

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"written: {n_written} stocks")
```

- 市場レジーム判定を実行する

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター計算（研究用）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

# 例: モメンタムの Z-score 正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- カレンダー取得 / 営業日判定

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- AI 使用箇所（news_nlp／regime_detector）は OpenAI API を利用します。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出しはネットワークアクセスを伴い、時間がかかることがあります。ログレベルを調整して実行状況を監視してください。

---

## 設定管理の挙動

- config.Settings により環境変数をラップしています。例: `from kabusys.config import settings; token = settings.jquants_refresh_token`
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml 探索）にある `.env` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイルとディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定 / .env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースを銘柄別に集約して LLM スコア化（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS 収集と前処理
    - calendar_management.py        — 市場カレンダーと営業日ユーティリティ
    - quality.py                    — データ品質チェック
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - audit.py                      — 監査ログテーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等
    - feature_exploration.py        — forward returns / IC / summary / rank
  - (その他: strategy, execution, monitoring モジュール群が __all__ に含まれる設計)

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス対策: 各処理は target_date を明示的に渡す設計です。バックテストや再現性を重視する場合は必ず過去日を明示してください。
- API レート制御: J-Quants クライアントは内部で 120 req/min を守るレートリミッタを持っていますが、運用時はネットワーク状況や並列実行に注意してください。
- AI 呼び出し: OpenAI API の呼び出しはコストとレート制限があります。バッチサイズやリトライ設定はファイル内定数で調整可能です。
- データ品質チェックは ETL の最後に実行され、問題検出時でも ETL は継続します（呼び出し元が停止判断を行う設計）。

---

## さらに

この README はコードベースの主要な機能と使い方の導入を説明するものです。各モジュールの詳細な API（関数引数、返り値、副作用）については、該当ソース内の docstring を参照してください。また実運用前に小さいデータセットで処理フローを検証することを推奨します。

質問や追加で README に含めたい項目（CLI 例、Docker 化手順、CI 設定など）があれば教えてください。