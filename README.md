# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリです。  
J-Quants / kabuステーション / OpenAI を組み合わせ、データETL、ニュースNLP、ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象とした次の用途を想定した Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント分析（銘柄単位）と市場レジーム判定
- 研究（ファクター計算、将来リターン・IC 計算、統計ユーティリティ）
- 監査ログテーブルの定義・初期化（発注シグナル→発注→約定のトレーサビリティ）
- データ品質チェックモジュール（欠損・重複・スパイク・日付不整合）

設計上の特徴：
- DuckDB を用いた高速かつローカルでの分析・永続化
- API 呼び出しはリトライ・レート制御を含めた堅牢設計
- ルックアヘッドバイアス回避を考慮した実装（内部で date.today() を不用意に参照しない）
- 冪等性・フェイルセーフを重視した実装方針

---

## 機能一覧

主な提供機能（モジュール）:

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と設定ラッパー（Settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB への保存）
  - pipeline: 日次 ETL（prices / financials / calendar）の実行と ETLResult
  - calendar_management: JPX カレンダー管理と営業日関連ユーティリティ
  - news_collector: RSS 収集、テキスト前処理、raw_news 保存（SSRF対策あり）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
  - stats: 共通統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメントを取得し ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime を作成
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（推奨環境）

- Python 3.10 以上（typing の新しい構文を使用）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml

（他に標準ライブラリと urllib/ssl 等を使用します）

パッケージ管理ファイルがある場合はそちらを参照してください。無ければ pip で個別に入れてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時: pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repository-url>
cd <repository>
```

2. 仮想環境を作成して有効化
```
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 依存パッケージをインストール
```
pip install duckdb openai defusedxml
# またはプロジェクトに setup/pyproject があれば:
pip install -e .
```

4. 環境変数を設定（.env / .env.local 推奨）
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（読み込みは OS環境変数より優先度が低い）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

推奨される環境変数（主要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（実行系を使う場合）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使用（任意だが一部機能で必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡単な例）

注意: 多くの API 呼び出しは DuckDB の接続（duckdb.connect("path")）を受け取ります。以下は Python スクリプト / REPL での使用例です。

- 日次 ETL を実行（prices / financials / calendar を取得・保存・品質チェック）
```
python - <<PY
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
PY
```

- ニュースのセンチメントスコアを取得して ai_scores テーブルへ保存
```
python - <<PY
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY が環境変数にある場合は None 可
print("書き込み銘柄数:", count)
PY
```

- 市場レジーム判定（ETF 1321 をベースに）
```
python - <<PY
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
PY
```

- 監査DBの初期化（監査テーブルの作成）
```
python - <<PY
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って発注監査ログを書き始められます
PY
```

- 研究用ファクター計算（例: momentum）
```
python - <<PY
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(len(records), "銘柄分のモメンタムを計算しました")
PY
```

---

## ディレクトリ構成

主要なファイル・モジュール（概観）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定のロード＆Settings クラス（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの OpenAI によるセンチメント解析・ai_scores 書き込み
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得/保存とリトライ・レート制御）
    - pipeline.py        — ETL パイプライン（run_daily_etl, run_*_etl）
    - calendar_management.py — 市場カレンダー・営業日ユーティリティと更新ジョブ
    - news_collector.py  — RSS 収集・前処理・raw_news 保存（SSRF 対策など）
    - quality.py         — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py           — 監査ログ DDL 定義・初期化
    - stats.py           — 共通統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（モメンタム/ボラ/バリュー）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - monitoring/, execution/, strategy/ など（パッケージ公開リストありが __all__ に含まれるが、ここに示されたファイルは機能群として存在）

（上記はリポジトリの主要モジュールを抜粋した概観です。実際のファイル・サブパッケージも合わせて参照してください。）

---

## 開発・テスト時の注意点

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env/.env.local を自動で読み込みます。
  - テスト等で自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI / J-Quants 呼び出し
  - 単体テストでは外部 API を叩かないようにモック（unittest.mock.patch）してください。モジュール内の _call_openai_api や jquants_client._request 等を差し替えやすい設計になっています。
  - OpenAI の JSON モードを利用して厳密な JSON を期待する処理が含まれますが、LLM の出力は常にバリデーションを行う実装です（不正なレスポンスはフェイルセーフでスキップし、ログを出力）。

- DuckDB の executemany と空リスト
  - 一部の実装は DuckDB の executemany が空リストを受け付けないことを考慮しており、空チェックを行っています。

- タイムゾーン
  - 監査ログ初期化時は接続のタイムゾーンを UTC にセットします（init_audit_schema 内で SET TimeZone='UTC' を実行）。

---

## 付記 / 参考

- 設計ドキュメント参照先（コード内コメントに DataPlatform.md / StrategyModel.md 等の参照がある旨が記載されています）。これらの設計資料が別途ある場合は参照してください。
- 実運用（live）では KABUSYS_ENV=live を設定し、適切な監視・リスク管理ルールを適用してください。
- セキュリティ: news_collector は SSRF 対策や XML パース時の defusedxml 使用、受信バイト制限などを実装していますが、利用環境に応じてさらに検査・制限を加えることを推奨します。

---

問題の報告や改善提案がある場合はリポジトリの Issue を作成してください。