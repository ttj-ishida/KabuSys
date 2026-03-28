# KabuSys

日本株自動売買プラットフォームのプロジェクトリポジトリ（ライブラリ）。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、特徴量計算・リサーチ、監査ログ（DuckDB）など自動売買に必要な基盤機能をモジュール化して提供します。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買基盤です。主な目的は以下：

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- RSS ニュース収集と LLM によるニュースセンチメント付与
- マーケットレジーム推定（ETF + マクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を DuckDB で管理

設計上の方針として「ルックアヘッドバイアス回避」を強く意識しており、日付参照は明示的な target_date をとる形で実装されています。

---

## 主な機能一覧

- 環境設定管理（.env の自動読み込み、必須設定の検証）
- J-Quants クライアント（レート制限・トークン自動更新・リトライ処理つき）
  - 株価日足（daily_quotes）
  - 財務データ（statements）
  - マーケットカレンダー
  - 上場銘柄情報
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）による銘柄別センチメントスコアリング（score_news）
- マーケットレジーム判定（ETF MA + マクロニュース LLM 組合せ、score_regime）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、z-score 正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ

---

## 必須・推奨環境変数

このライブラリはいくつかの環境変数を参照します（.env の利用を想定）。

必須（未設定時は ValueError）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注に使用する場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV — 環境: one of "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI を使う機能（score_news / score_regime）で参照（関数引数から渡すことも可能）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

.example:
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境（3.9+ 推奨）を用意します。

2. 依存ライブラリをインストール（プロジェクトの requirements.txt がない場合の例）:
   ```
   pip install duckdb openai defusedxml
   ```
   — その他、実行環境によって urllib 等標準ライブラリのみで動作しますが、OpenAI SDK と duckdb は必須です。

3. リポジトリルートに `.env`（および必要なら `.env.local`）を作成し、上記必須変数を設定します。`.env.example` を参考にしてください（プロジェクトに同梱されている想定）。

4. データディレクトリを用意（必要に応じて）:
   ```
   mkdir -p data
   ```

5. DuckDB の初期化（監査ログ用 DB を作る例）:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要 API のサンプル）

以下は簡単な Python からの呼び出し例です。各関数は明示的に duckdb 接続や target_date を受け取る設計です（ルックアヘッド回避）。

1) DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

2) ニュースの NLP スコアを作成する（OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
conn.close()
```

3) 市場レジームをスコアリングする:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

4) 監査ログスキーマを既存の DuckDB 接続に追加:
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
conn.close()
```

5) 研究用ユーティリティ（例: momentum）:
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, date(2026, 3, 20))
# recs は {"date","code","mom_1m",...} の dict のリスト
conn.close()
```

注意:
- OpenAI 呼び出しを行う機能は API キー（OPENAI_API_KEY）を必要とします。関数呼び出し時に api_key を明示的に渡すこともできます。
- ETL / ニュース収集 / LLM 呼び出しは外部ネットワークを利用するため、適切なネットワーク設定と API レート制限を守ってください。

---

## ディレクトリ構成（主なファイル）

プロジェクト内の主なモジュールとファイルは以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント付与（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS ニュース収集
    - calendar_management.py     — マーケットカレンダー管理
    - stats.py                   — z-score 正規化などの統計ユーティリティ
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py     — forward returns, IC, summary, rank
  - ai/, data/, research/ などの細かな実装ファイル（上記に続く）

上記以外にドキュメントや設定ファイル（pyproject.toml, .env.example 等）がプロジェクトルートに存在する想定です。

---

## 注意事項 / 運用上のヒント

- ルックアヘッドバイアス防止: 各処理は target_date を明示的に与えることを想定しています。日付を自動決定したい場合でも、バックテスト等では必ず過去時点のデータのみを参照するようにしてください。
- OpenAI の呼び出しは失敗時にフェイルセーフ（スコア 0 にフォールバック）する実装になっている関数が多いですが、ログを確認してください。
- .env 自動読み込みを無効化したいテスト等では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスは settings.duckdb_path で確認・変更できます（環境変数 DUCKDB_PATH）。

---

## ライセンス・貢献

（この README にはライセンス情報が含まれていません。実際のリポジトリでは LICENSE を参照してください。）  
バグ報告・機能提案・プルリクエストはリポジトリに沿った貢献フローでお願いします。

---

以上が本コードベースの利用開始ガイドです。必要でしたらサンプルの .env.example、requirements.txt（推奨依存一覧）、および具体的な運用手順（cron/ジョブ定義や Slack 通知のサンプル）を追加で作成します。どの部分を優先して詳しくしたいか教えてください。