# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL、ニュース収集・NLP（LLM を用いたセンチメント）、ファクター計算、監査ログ（トレーサビリティ）などを含む、バックテスト／本番運用に対応したユーティリティ群を提供します。

主な設計方針は以下のとおりです。
- Look‑ahead bias を避ける（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB をデータプラットフォームに採用（SQL + Python の組合せで高速処理）
- 外部 API 呼び出しはリトライ・レート制御等を含む頑健な実装
- 冪等性・監査（履歴保存）重視

---

## 機能一覧

- 環境設定管理
  - .env ファイルや環境変数から設定を自動読み込み（自動読み込みは無効化可能）
  - 必須設定の検査（未設定時は ValueError）

- Data (ETL / News / J-Quants クライアント)
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
    - レートリミッティング、指数バックオフ、トークン自動リフレッシュに対応
  - ETL パイプライン（日次 ETL: カレンダー → 株価 → 財務 → 品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS）と前処理（URL 正規化、SSRF 対策、gzip 対応）
  - データ品質チェック（欠損・スパイク・重複・将来日付等）
  - 監査ログ（signal_events / order_requests / executions）テーブル作成ユーティリティ

- Research（ファクター計算・探索）
  - Momentum / Volatility / Value 等ファクター計算
  - 将来リターン計算（複数ホライズン）
  - IC（Spearman rank）計算、統計サマリー
  - z-score 正規化ユーティリティ

- AI（LLM を用いる処理）
  - ニュースの銘柄ごとセンチメントスコア化（gpt-4o‑mini を想定）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）

- その他ユーティリティ
  - DuckDB 監査用 DB 初期化
  - 各種トランザクション／冪等保存ロジック

---

## 必要条件（推奨）

- Python 3.10+（typing の union 演算子 `|` を使用）
- duckdb
- openai（OpenAI Python SDK、LLM 呼出し用）
- defusedxml（RSS パースの安全化）
- （標準ライブラリ以外の依存はプロジェクトの packaging / requirements.txt を参照してください）

pip 例（プロジェクトに requirements.txt がある想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または最低限:
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

このプロジェクトは .env ファイル（プロジェクトルート）または環境変数から設定を読み込みます。自動読み込みはデフォルト有効です（CWD ではなくパッケージ位置からプロジェクトルートを検出）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN - J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      - kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       - Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      - Slack チャンネル ID（必須）
- OPENAI_API_KEY        - OpenAI API キー（AI 関連関数を使うときに必要）
- DUCKDB_PATH           - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           - SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             - ログレベル: DEBUG/INFO/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD - 1 をセットすると .env 自動読み込みを無効化

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env の自動ロードは OS 環境変数より低優先度（.env.local は上書き）ですが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url> kabusys
   cd kabusys
   ```

2. 仮想環境の作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .     # パッケージとしてインストール可能なら
   # または:
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートします（上記参照）。

4. DuckDB ファイルやデータディレクトリを準備
   - デフォルトでは data/ 以下にファイルを作成します。必要に応じてディレクトリを作成してください:
     ```bash
     mkdir -p data
     ```

---

## 使い方（主なサンプル）

Python から直接呼び出して利用するパターンを示します。すべての関数は duckdb の接続オブジェクトを受け取る設計です。

- ETL（日次 ETL の実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
# 監査テーブルが作成された接続を返す
```

- ファクター計算 / リサーチ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- データ品質チェック
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点:
- OpenAI を呼ぶ関数は api_key 引数を受け取るか、環境変数 OPENAI_API_KEY を参照します。
- DuckDB のバージョンや SQL バインド挙動に注意（コード内で互換性対策済みの箇所あり）。
- ETL / API 呼出しは外部ネットワークを使用するため、適切な認証情報を設定してください。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    — .env / 環境変数読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（銘柄別スコアリング）
    - regime_detector.py         — マクロ + MA200 合成で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save）
    - pipeline.py                — ETL パイプラインと run_daily_etl 等
    - etl.py                     — ETLResult の再エクスポート
    - news_collector.py          — RSS 収集・前処理・SSRF 対策
    - calendar_management.py     — 市場カレンダー管理（営業日判定等）
    - quality.py                 — データ品質チェック
    - stats.py                   — 汎用統計ユーティリティ（zscore）
    - audit.py                   — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Volatility/Value 計算
    - feature_exploration.py     — forward returns / IC / summary / rank

（上記以外に strategy, execution, monitoring 等のパッケージが __all__ に登録される想定。実装は別ファイル/モジュールで管理されます。）

---

## セキュリティ・運用上の注意

- ニュース収集には SSRF 対策や受信サイズ上限、XML の安全パース（defusedxml）等が組み込まれていますが、運用環境のネットワーク制限やファイアウォールによる追加対策を推奨します。
- J-Quants API はレート制限（120 req/min）を守るよう実装されていますが、追加の分散実行や API キューを導入する場合は運用設計を見直してください。
- 実取引環境（live）では KABUSYS_ENV を "live" に設定してください。paper_trading モードの挙動はコード内で分岐する可能性があります。
- 自動ロードされる .env の扱いに注意。CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って外部影響を防ぐことができます。

---

## 開発・テスト

- 単体テスト用に関数が設計されており、外部 API 呼び出しはモック可能（例: news_nlp._call_openai_api の patch 等）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を有効化して環境の差異を抑えると良いです。

---

## ライセンス / コントリビューション

（この README にはライセンス・貢献ルールの記載はありません。リポジトリの LICENSE / CONTRIBUTING を参照してください。）

---

以上がこのコードベースの概要と基本的な使い方・構成です。必要であれば README を拡張して、コマンドラインツール例、CI 設定例、詳細な .env.example、テーブルスキーマ一覧などを追記できます。どの部分の記述を詳しくしたいか教えてください。