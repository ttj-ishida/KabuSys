# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォームと自動売買インフラのコアライブラリです。  
データ収集（J-Quants / RSS）、品質チェック、ファクター計算、AI を用いたニュースセンチメント評価、監査ログ、ETL パイプライン等を含むモジュール群を提供します。

主な用途の想定例:
- 日次 ETL（株価 / 財務 / 市場カレンダー）の自動取得・保存
- ニュース記事の収集・AI による銘柄センチメント評価
- 市場レジーム判定（MA + マクロニュース LLM 合成）
- 研究用ファクター計算・特徴量探索
- 発注前後の監査ログ（監査テーブル初期化・操作）

---

## 機能一覧

- 設定管理
  - .env ファイル / 環境変数の自動読み込み（パッケージ配布後も動作するようプロジェクトルート検出）
  - 必須設定の検査（Settings クラス）
- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（fetch / save の冪等処理、リトライ・レート制御）
  - RSS ベースのニュース収集（SSRF 保護、URL 正規化、前処理）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ETL パイプライン（run_daily_etl、個別ジョブ run_prices_etl 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブルと初期化）
- AI（kabusys.ai）
  - news_nlp.score_news: ニュースを銘柄単位にまとめて LLM でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日 MA とマクロニュース LLM を組み合わせて市場レジーム判定
  - LLM 呼び出しは OpenAI SDK（gpt-4o-mini）を利用（JSON Mode）
- リサーチ（kabusys.research）
  - ファクター計算（mom, volatility, value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - DuckDB を用いたデータ保存・クエリを前提とした実装

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多いですが、上記は本プロジェクトの主要外部依存です）

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください。）

---

## 環境変数（主なもの）

以下は本プロジェクトで期待される主な環境変数例です。README 内の例は .env に定義し、自動ロードさせるのが簡便です。

必須:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

任意 / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
- OPENAI_API_KEY — LLM 呼び出しに必要（引数で注入することも可能）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化（テスト用）

.example の .env（参考）
```
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- パッケージ開始時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
- Settings クラスは不足している必須変数を要求し、未設定の場合は ValueError を投げます。

---

## セットアップ手順（ローカル開発・動作確認用）

1. リポジトリをクローン
```
git clone <repo_url>
cd <repo>
```

2. Python 仮想環境を作成・有効化
```
python -m venv .venv
# Unix/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 依存パッケージをインストール
（プロジェクトに requirements / pyproject があればそちらを使ってください。以下は主要依存の例）
```
pip install duckdb openai defusedxml
# 開発時に editable インストール
pip install -e .
```

4. 環境変数を設定
- ルートに `.env` を作成するか、必要な環境変数をシェルでエクスポートします。
- 例: `.env` をプロジェクトルートに配置（上の .env.example を参照）

5. DuckDB ファイルや監査 DB を初期化（任意）
Python REPL やスクリプトで:
```python
import duckdb
from kabusys.data import audit, jquants_client
from kabusys.config import settings

# DuckDB メイン接続（settings.duckdb_path を使用）
conn = duckdb.connect(str(settings.duckdb_path))

# 監査スキーマを初期化したい場合
from pathlib import Path
audit.init_audit_schema(conn, transactional=True)

# または専用ファイルで監査 DB を作る
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的なワークフロー）

以下はライブラリ API を直接使う簡単な例です。プロダクションではジョブスケジューラ（cron / Airflow 等）から呼び出す想定です。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai_scores")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / 研究用ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))

# Zスコア正規化
normed = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])
```

- 監査ログ用 DB の初期化（専用ファイル）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 order_requests / executions 等をこの DB に保存して監査を行う
```

注意点:
- OpenAI（LLM）呼び出し系（news_nlp, regime_detector）は OPENAI_API_KEY を環境変数または api_key 引数で渡す必要があります。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN および get_id_token() の動作に依存します。
- ETL / API 呼び出しはネットワークエラー時のリトライ・バックオフを実装していますが、API 利用制限や料金に注意してください。

---

## 主要モジュール・ディレクトリ構成（概要）

リポジトリの主なディレクトリ / ファイルは以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを LLM でセンチメント化して ai_scores に保存
    - regime_detector.py     — MA200 とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save / auth）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS フィード収集・前処理
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン, IC, factor_summary, rank
  - ai/ (上記)
  - research/ (上記)

（実際のリポジトリに他のサブディレクトリや CLI、サンプルスクリプト、テスト、pyproject.toml 等がある場合はそれらを参照してください）

---

## 開発・運用に関する注意点

- Look-ahead bias の防止に設計上配慮している:
  - 各関数は内部で date.today() を直接参照しない（target_date を引数で受け取る設計）
  - データ読み取りは target_date 未満 / 以前の制約を適切に使用
- ニュース収集では SSRF / XML 攻撃 / 圧縮爆弾対策を実装
- J-Quants クライアントはレート制御、401 時のトークン自動リフレッシュ、リトライを実装
- DuckDB を前提としており、SQL クエリはパラメータバインド（?）を利用してインジェクションを排除
- LLM 呼び出しは OpenAI SDK を利用（JSON Mode を利用して厳格な JSON 出力を期待）
- 本リポジトリは実際の発注や資金を扱う運用向けの慎重なレビューが必要（live 環境で実行する前に paper_trading / development で十分な検証を推奨）

---

## 貢献・拡張

- 新しい ETL ソースやフィードを追加したい場合は data/*.py にクライアント / save_* を追加してください。
- LLM プロンプトやモデル変更は ai/news_nlp.py / ai/regime_detector.py を編集してください（API リトライロジックとレスポンスバリデーションに注意）。
- 監査ログスキーマの拡張は data/audit.py に新たなテーブル・インデックスを追加し、init_audit_schema を通じて初期化してください。

---

この README はリポジトリ内のコードドキュメントを基に作成しています。実行・デプロイの際は実際の pyproject.toml / requirements.txt / docker 構成や運用ドキュメントに従ってください。必要であれば README を元に手順書や運用ガイドの作成を支援します。