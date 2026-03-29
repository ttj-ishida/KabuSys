# KabuSys — 日本株自動売買基盤 (README)

KabuSys は日本株向けのデータプラットフォーム & 自動売買インフラのコアライブラリです。本リポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、市場レジーム判定、ファクター計算、監査ログなどの主要コンポーネントを含みます。

---

## プロジェクト概要

目的:
- J-Quants API や RSS などから市場データ・ニュースを取得して DuckDB に保存
- データ品質チェックと ETL パイプラインを提供
- ニュースを LLM（OpenAI）で解析して銘柄別スコアを生成
- ETF を用いた市場レジーム判定（MA と マクロニュースの組合せ）
- 監査ログ（signal → order → execution のトレーサビリティ）を DuckDB に保持
- 研究用モジュール（ファクター計算、特徴量探索）を提供

設計方針の特徴:
- ルックアヘッドバイアスを避ける（date/target_date を明示的に扱う）
- DuckDB を中心としたローカル分析基盤
- API 呼び出しはリトライやレート制御を実装しフェイルセーフ化
- JSON Mode を使った厳格な LLM レスポンスバリデーション

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得（pagination 対応）
  - ETL の差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL のエントリポイント: run_daily_etl

- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks による一括実行

- ニュース収集・NLP
  - RSS 収集（トラッキングパラメータ削除、SSRF 対策、gzip 制限、XML の安全パース）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコア生成（score_news）
  - レスポンスの厳密なバリデーションとリトライ

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM スコアを合成して日次レジーム判定（score_regime）

- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- 監査ログ（Audit）
  - signal_events, order_requests, executions 等のテーブル定義と初期化ユーティリティ
  - init_audit_db / init_audit_schema による冪等的セットアップ

---

## 必要条件 / 依存関係

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外は requirements.txt がある場合はそちらを利用してください（本コードベースは最小限の外部依存を前提に実装されています）。

（pip での例）
```bash
pip install duckdb openai defusedxml
```

---

## 環境変数（必須 / 主要）

KabuSys は .env（プロジェクトルート）およびシステム環境変数を自動ロードします（.git または pyproject.toml を起点にプロジェクトルートを検出）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視データ等の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

注意:
- settings（kabusys.config.settings）経由で上記を参照します。必須変数が未設定のままアクセスすると ValueError を送出します。

---

## セットアップ手順（例）

1. リポジトリをクローン
```bash
git clone <repo_url>
cd <repo_root>
```

2. Python 仮想環境を作る（推奨）
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存ライブラリをインストール
```bash
pip install -r requirements.txt
# または最低限:
pip install duckdb openai defusedxml
```

4. 環境変数設定
- プロジェクトルートに `.env`（および必要なら `.env.local`）を作成して必要なキーを設定してください。
- 例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```
- 自動ロードをオフにしたい場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（主要な関数・実行例）

ここでは Python REPL やスクリプトからの呼び出し例を示します。すべての関数は明示的に DuckDB 接続と target_date（または date）を受け取る設計です（ルックアヘッドを避けるため）。

- DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア生成（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} scores")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー更新ジョブ（calendar_update_job）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- 監査ログ DB 初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成される
```

- 研究系関数（例: モメンタム計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリスト
```

---

## 注意点 / 運用上のヒント

- ルックアヘッドバイアス防止:
  - 多くの関数が内部で datetime.today() を参照せず、必ず target_date を引数で受け取ります（バックテストでの安全性）。
- OpenAI 呼び出し:
  - API レスポンスのパース失敗や API エラー時はフェイルセーフでスコア 0.0 を使う設計の箇所があります（ログを確認ください）。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化してください。
- DuckDB executemany による空リストを避けるため、モジュール側でも空チェックが入っています。
- J-Quants API はレート制限があるため、jquants_client は内部で固定間隔スロットリングとリトライを行います。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — カレンダー管理・営業日判定
  - etl.py — ETL Result の公開
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログ初期化（init_audit_db / init_audit_schema）
  - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
  - news_collector.py — RSS 収集 / 前処理
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記はコードベースに含まれる主なモジュール構成です）

---

## ロギング / デバッグ

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- ETL など長い処理は関数内部で詳細な logger.debug/info/warning を出力します。運用時はログを集約・永続化してください。

---

## 貢献 / テスト

- テストについてはユニットテストが別途存在することを想定しています（モジュール内で関数差し替え（モック）できるよう設計）。
- OpenAI 呼び出しやネットワーク関連はモック化してテストしてください（score_news、regime_detector、news_collector 等は外部呼び出しを多く含みます）。

---

もし README に追加したい実行スクリプト例（systemd / cron / Airflow ジョブ定義）や .env.example のテンプレートが必要であれば、環境や運用要件に合わせたサンプルを作成します。どの例が欲しいか教えてください。