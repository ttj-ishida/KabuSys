# KabuSys

日本株向けのデータプラットフォーム & 自動売買リサーチ基盤。J-Quants / kabuステーション / RSS / OpenAI を組み合わせて、データ取得（ETL）・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです:

- J-Quants API から株価・財務・上場情報・市場カレンダーを差分取得して DuckDB に保存する ETL
- 生データの品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集（raw_news）と銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄ごとの ai_score）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用途のファクター計算・IC / 将来リターン計算・Zスコア正規化
- 発注・約定までのトレーサビリティを担保する監査ログスキーマ（DuckDB）

設計上の特徴:
- ルックアヘッドバイアス防止（内部で date.today() を無作為参照しない設計を意識）
- DuckDB をデータレイヤに採用（軽量でローカル分析に適合）
- 冪等な DB 書き込み（ON CONFLICT / INSERT ... DO UPDATE 等）
- API 呼び出しはレート制御・リトライを実装

---

## 主な機能一覧

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: 認証・ページネーション・保存関数
- データ品質:
  - check_missing_data, check_spike, check_duplicates, check_date_consistency（kabusys.data.quality）
  - run_all_checks（品質チェックまとめ）
- ニュース:
  - RSS 収集・前処理（kabusys.data.news_collector）
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込み
- AI / レジーム:
  - ai.news_nlp.score_news（銘柄ごとのニューススコア）
  - ai.regime_detector.score_regime（ETF MA200 とマクロセンチメントを合成して market_regime に保存）
- 研究用:
  - research.factor_research: calc_momentum, calc_value, calc_volatility
  - research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize（Zスコア正規化）
- 監査ログ:
  - data.audit.init_audit_schema / init_audit_db（signal_events, order_requests, executions テーブルを初期化）

---

## 必要環境 / 依存

- Python >= 3.10（型注釈の union 表記 等のため）
- 必須パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）を広く使用

（プロジェクトに requirements.txt がある場合はそれを使ってください。なければ上記パッケージを pip で導入してください。）

例:
```
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（読み込みはプロジェクトルートを .git または pyproject.toml から探索して決定）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知機能で使用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector で使用）

.env の例（テンプレートを .env.example として用意する想定）:
```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存をインストール
   ```
   pip install -r requirements.txt   # もし用意されていれば
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数をシェルにエクスポートしてください。
   - 自動読み込みを無効化したい場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下はライブラリ呼び出しの最小例です。スクリプトやジョブの中から呼び出して利用します。

- DuckDB 接続の作成（監査DB 例）
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ファイル作成 + スキーマ初期化
```

- ETL を日次実行する（J-Quants トークンは環境変数経由）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, target_date=date(2026,3,20))
v = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

注意:
- OpenAI API を利用する関数は `OPENAI_API_KEY` または関数引数で API キーを渡す必要があります。
- run_daily_etl 等は内部で外部 API を呼ぶため、ネットワークおよび API トークンが必要です。

---

## よくあるジョブ例

- 夜間 ETL バッチ: run_daily_etl を cron / Airflow 等から daily 実行
- ニュース収集ジョブ: RSS フィード取得 → raw_news に保存 → score_news で ai_scores を更新
- レジーム判定ジョブ: 毎営業日 market_regime を更新（score_regime）
- 監査テーブル初期化: init_audit_db で監査 DB を生成

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング（score_news）
    - regime_detector.py  — MA200 とマクロセンチメントの合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント (fetch / save 関数)
    - pipeline.py         — ETL パイプラインの実装（run_daily_etl 等）, ETLResult
    - etl.py              — ETL インターフェース再エクスポート
    - news_collector.py   — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py          — データ品質チェック（QualityIssue）
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ定義 / 初期化（signal_events / order_requests / executions）
    - (その他)            — 保存・ユーティリティ関数群
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン / IC / summary / rank
  - (その他モジュールやサブパッケージ)

---

## 運用上の注意

- 本パッケージは実際の売買発注システムの一部を想定しているため、実運用（本番）での使用は慎重に行ってください。KABUSYS_ENV を `live` にすると本番向け動作フラグが有効になりますが、実際の注文処理モジュールやブローカ連携については別途実装と安全策が必要です。
- OpenAI 呼び出しはコスト・レート制限があるため、バッチ設計やリトライ設定に注意してください。APIキーは漏洩しないよう管理してください。
- ETL/保存処理は冪等性を考慮していますが、データ整合性のためバックアップや監査ログを有効にしてください。

---

## 貢献 / 開発

- テストはユニットテスト / モックを活用して API 呼び出し部分を差し替える形で行ってください（kabusys.ai.news_nlp/_call_openai_api 等は patch で差し替え可能に設計）。
- 新しい RSS ソースは `kabusys.data.news_collector.DEFAULT_RSS_SOURCES` を拡張してください。
- バグレポート・機能提案は issue を立ててください。

---

必要なら README に含めるサンプル .env.example、requirements.txt、または具体的な Cron / systemd ジョブ例も作成します。どれを追加しますか?