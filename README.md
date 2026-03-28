# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、データ品質チェック、特徴量計算、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の研究・運用パイプラインを構築するためのモジュール群です。主に以下を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（DuckDB 保存・冪等性）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集・前処理と OpenAI を使った銘柄別センチメント評価（ai_scores）
- 市場レジーム判定（ETF + マクロニュースの LLM スコアを合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 発注・約定を追跡する監査ログスキーマ（DuckDB）と初期化ユーティリティ
- 環境変数管理（.env の自動読み込み、必須値チェック）

設計上の共通方針として「ルックアヘッドバイアスを防ぐ（date を引数化）」「冪等処理」「外部 API のリトライ／フェイルセーフ」「DuckDB を中心としたローカル永続化」が採用されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークン管理・レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（prices/financials/calendar）
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - news_collector: RSS 取得・前処理・保存（SSRF 対策・トラッキング除去）
  - calendar_management: 営業日判定・next/prev/get_trading_days、calendar_update_job
  - audit: 監査ログテーブル DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats: 汎用統計（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数管理（.env 自動ロード、必須チェック、settings オブジェクト）

---

## 動作要件（推奨）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml

開発環境では pip の仮想環境を使うことを推奨します。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
pip install -e .
```

（プロジェクト配布に requirements.txt があればそれを利用してください）

---

## 環境変数 / .env

パッケージはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（CWD に依存せずパッケージファイル位置を起点に探索）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（jquants_client.get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector などに使用）
- KABU_API_PASSWORD: kabu API パスワード（発注実装がある場合に使用）
- SLACK_BOT_TOKEN: Slack 通知用（必要なら）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID

その他（任意／デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）

例 `.env.example`:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CHXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

設定値はコード内の `kabusys.config.settings` から参照できます。
例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## セットアップ手順（概要）

1. リポジトリをクローン / ソースを取得
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（duckdb / openai / defusedxml など）
4. プロジェクトルートに `.env` を作成して必須値を設定
5. DuckDB ファイルディレクトリなどの作成（パスは settings.duckdb_path を参照）

例:
```
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# (任意) pip install -e .
cp .env.example .env
# .env にトークン等を記入
```

---

## 使い方（代表的な API と実行例）

下記は一例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す connection）を受け取ります。

1) 日次 ETL を実行する（prices/financials/calendar の差分取得・保存・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

戻り値は ETLResult オブジェクト（取得数・保存数・品質問題リスト・エラー一覧などを含む）。

2) ニュースの NLP スコアを入れる（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```
- `OPENAI_API_KEY` を環境変数か引数 `api_key` で渡してください。
- 関数は raw_news, news_symbols, ai_scores テーブルを使用します。

3) 市場レジームを判定して保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```
- ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成します。
- `OPENAI_API_KEY` を環境変数か引数 `api_key` で渡してください。

4) 監査ログ（発注・約定）用のスキーマを初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 返り値は duckdb.DuckDBPyConnection
```

5) データ品質チェックを個別に実行する
```python
from kabusys.data.quality import run_all_checks
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- すべての「日付」は関数引数で明示的に渡す設計（内部で datetime.today() を参照しない）ため、バッチやバックテストでルックアヘッドバイアスを防止できます。
- OpenAI 呼び出しはリトライやフォールバック（失敗時は 0.0）を備えていますが、API キーの制限やコストに注意してください。

---

## ディレクトリ構成（主要ファイル）

概略:
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ pipeline.py
   │  ├─ etl.py
   │  ├─ quality.py
   │  ├─ news_collector.py
   │  ├─ calendar_management.py
   │  ├─ stats.py
   │  └─ audit.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   └─ ai/ (上記)
```

各モジュールの役割は前節の機能一覧とソース内ドキュメンテーション（docstring）に記載されています。実装は DuckDB を中心としており、ETL・分析・NLP スコアリング・監査ログそれぞれが分離されています。

---

## テスト / 開発時の便利な環境変数

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  
  tests や CI で .env の自動読み込みを無効にしたい場合に設定します。

- OPENAI_API_KEY を直接テスト関数に渡してモック化することを推奨（外部 API 呼び出しは unittest.mock で差し替え可能）。

- news_nlp._call_openai_api / regime_detector._call_openai_api などはユニットテストで patch して応答を制御できます。

---

## 追加の注意点 / ベストプラクティス

- J-Quants トークン・OpenAI API キー等の機密情報は .env を使用し、リポジトリに含めないでください。
- ETL を定期実行する際はモニタリングと品質チェック通知（例: Slack）を組み合わせてお使いください。
- DuckDB ファイルはバックアップ/パーミッション管理を適切に行ってください（特に運用環境）。
- OpenAI の課金・レート制限に注意し、必要に応じてバッチサイズやモデルを調整してください。

---

## 参考・問い合わせ

ソース中に詳細な docstring と設計注記があるので、機能の使い方や設計理由は各モジュールを参照してください。実装や拡張に関する質問はリポジトリの Issue や担当者までお問い合わせください。

--- 

以上。README の内容はプロジェクトの実装・運用ポリシーに応じて適宜修正・追記してください。