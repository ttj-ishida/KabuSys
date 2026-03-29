# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ（トレーサビリティ）、J-Quants / Slack / kabu ステーション連携などを提供します。

---

## プロジェクト概要

KabuSys は日本株投資戦略の研究〜運用パイプラインを支える内部ライブラリ群です。主な役割は以下です。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に格納する ETL
- RSS ニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄毎 / マクロ）
- マーケットレジーム判定（ETF とマクロセンチメントの合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と研究支援ユーティリティ
- データ品質チェック・監査ログスキーマ（signal → order → execution のトレーサビリティ）
- 環境設定管理（.env の自動読み込みと settings）

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時はスキップ）」を重視しています。

---

## 機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダー管理（営業日判定, next/prev_trading_day）
  - ニュース収集（RSS fetch_rss、前処理、DB への保存想定）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロニュースの LLM スコアを合成して market_regime に保存
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数経由の設定取得（自動 .env ロード機能あり）
- audit
  - 監査テーブル DDL / インデックス、DuckDB 初期化ヘルパー

---

## セットアップ手順

以下はローカル開発／実行環境の例です。

1. リポジトリをクローン
   - 仮にプロジェクトルートに `pyproject.toml` / `.git` がある想定です。

2. Python 仮想環境作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   ※ プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを利用してください。最低限必要なパッケージ例:

   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   （Slack 連携やその他機能を使う場合は slack_sdk 等の追加が必要になる可能性があります。）

4. パッケージを編集可能インストール（開発時）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（起動時に config モジュールが読み込み）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（名前を正確に指定しています）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: environment（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime が参照）

   ※ .env の書式は一般的な KEY=VALUE に対応。`export KEY=val` 形式や quoted value の扱いに対応しています。

---

## 使い方（例）

ここでは主要なユーティリティの簡単な使い方を示します。実行は Python スクリプトまたは REPL で行います。

基本的に DuckDB 接続を渡して各関数を呼びます（DuckDB はファイルベースのため簡単に永続化できます）。

1) DuckDB 接続の作成と ETL 実行

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path 型
conn = duckdb.connect(str(settings.duckdb_path))  # 例: data/kabusys.duckdb

# 日次 ETL（target_date を指定しないと今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄ごと）スコアリング

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュース合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

4) ファクター計算（研究用）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

5) 監査ログ（audit）スキーマ初期化

```python
from kabusys.data.audit import init_audit_db

# ":memory:" でインメモリ DB、またはファイルパスを指定
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) が作成されます
```

6) 設定取得（Settingsの利用例）

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- AI 関連関数は OpenAI の API キーを必要とします。api_key 引数を指定するか環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出しはネットワーク依存のため、実行時のネットワーク・API レスポンスにより処理がスキップされる場合があります。ログを確認してください。

---

## よくある操作とヒント

- .env の自動読み込み:
  - モジュール import 時にプロジェクトルート（.git または pyproject.toml を親ディレクトリで探索）を検出すると `.env` / `.env.local` を自動で読み込みます。
  - テストや CI で自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- OpenAI 呼び出しのフェイルセーフ:
  - news_nlp / regime_detector の両方とも API エラー時はログを出しつつデフォルト値（例: macro_sentiment=0.0）にフォールバックします。これによりパイプラインが致命停止しにくく設計されています。

- DuckDB executemany の注意:
  - 一部の処理は DuckDB の executemany に空リストを渡せない制約を避けるため事前に空チェックしています。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - Settings クラス、.env 自動読み込み、主要環境変数定義
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — ETF とマクロで市場レジームを判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（fetch / save / get_id_token）
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py             — ETLResult を再エクスポート
  - news_collector.py  — RSS 収集 / 前処理 / SSRF 対策
  - calendar_management.py — 市場カレンダー管理（営業日判定）
  - stats.py           — zscore_normalize 等の統計ユーティリティ
  - quality.py         — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit.py           — 監査ログスキーマ定義 & 初期化
- src/kabusys/research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- src/kabusys/ai/__init__.py

（上記に加え、プロジェクトルートに pyproject.toml / requirements.txt / .env.example 等がある想定です）

---

## ログとデバッグ

- 設定: LOG_LEVEL 環境変数でログレベルを制御（デフォルト INFO）。
- ETL / AI 呼び出しは警告や例外をログに出します。問題発見時はログをまず確認してください。

---

## 補足（設計上の注意）

- ルックアヘッドバイアス防止: 多くの関数（ETL・AI・research の日付処理）は datetime.today()/date.today() を直接参照しないように設計されています。必ず target_date を明示して使用することが推奨されます。
- 冪等性: DB 保存関数は ON CONFLICT（あるいはユニークキー）で上書きするため、再実行しても安全な設計になっています。
- フェイルセーフ: 外部 API が失敗しても処理全体が止まらないよう、スコアのデフォルトや例外吸収の戦略が採られています。

---

必要であれば、README に含めるサンプル .env.example、インストール用の requirements.txt、あるいは具体的な CLI / systemd / cron の実行例（ETL の定期実行設定）なども作成できます。どの部分を詳しくしたいか教えてください。