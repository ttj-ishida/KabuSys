# KabuSys

日本株のデータプラットフォームと自動売買・リサーチ基盤のライブラリです。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（オーダー/約定追跡）などの機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API からの株価日足、財務データ、マーケットカレンダー取得（ページネーション対応・リトライ・レートリミット）
  - 差分更新 / バックフィル機能
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理・NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュース + MA200 乖離で市場レジーム判定（score_regime）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ、Z スコア正規化
- 監査（Audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ（監査ログ）
- ユーティリティ
  - 環境設定読み込み（.env 自動読み込み、環境変数優先）
  - 汎用統計関数（zscore_normalize）など

---

## 必要条件 / 推奨環境

- Python 3.10+
- 依存ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- （開発）pipenv / poetry / virtualenv など仮想環境を推奨

requirements.txt / pyproject.toml がある前提でインストールしてください。例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"   # or pip install -r requirements.txt
```

（注）実行環境により追加の依存が必要な場合があります。OpenAI クライアントや duckdb は明示的に必要です。

---

## 環境変数 / .env

プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に置いた `.env` / `.env.local` を自動読み込みします。OS 環境変数が優先され、`.env.local` は `.env` を上書きできます。自動ロードを無効化するには:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（README 用抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV: environment (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）

例 `.env`（サンプル）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存をインストール
   - pip install -e . や pyproject.toml / requirements.txt に従ってインストール
4. プロジェクトルートに `.env` を作成し、上記の必須キーを設定
5. DuckDB ファイルのディレクトリを作成（`data/` 等）
6. 初期スキーマや監査 DB を必要に応じて初期化

---

## 使い方（主要な例）

以下はライブラリ API の一例です。各モジュールは duckdb の接続（duckdb.connect(...)）を引数として受け取る設計です。

- ETL（日次パイプライン実行）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 30))
print(result.to_dict())
```

- ニュースセンチメント (OpenAI を使用)

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
n = score_news(conn, target_date=date(2026, 3, 30), api_key=None)
print(f"scored {n} tickers")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 30), api_key=None)
```

- 監査ログの初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使うか別 DB を指定
conn = init_audit_db(settings.duckdb_path)
# これで signal_events / order_requests / executions テーブルが作成される
```

- 研究用関数例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
recs = calc_momentum(conn, target_date=date(2026, 3, 30))
# recs は [{'date': date, 'code': 'XXXX', 'mom_1m': ..., ...}, ...]
```

注意:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。各関数はテスト容易性のため api_key を引数で受け取れる設計です。
- 多くの DB 書き込み関数は冪等（ON CONFLICT / DELETE→INSERT 等）を意識しています。

---

## 開発・テストのヒント

- 自動環境読み込みを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（ユニットテスト時に便利）。
- OpenAI / ネットワーク呼び出しはモック可能:
  - ai.news_nlp._call_openai_api や ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えてテストできます。
- DuckDB の executemany に空リストを渡すとエラーになるため、コード内で空チェックが入っています。ユニットテストでもこれを考慮してください。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP スコアリング
    - regime_detector.py        — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント & 保存処理
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETL 公開インターフェース（ETLResult）
    - calendar_management.py    — マーケットカレンダー管理
    - news_collector.py         — RSS ニュース収集
    - quality.py                — データ品質チェック
    - stats.py                  — 統計ユーティリティ（zscore_normalize）
    - audit.py                  — 監査ログ定義と初期化
  - research/
    - __init__.py
    - factor_research.py        — Momentum/Value/Volatility 等
    - feature_exploration.py    — forward returns / IC / summary / rank
  - research/（その他ファイル）
- pyproject.toml / setup.cfg / requirements.txt 等（プロジェクトルート）

---

## 設計上の注記

- Look-ahead bias を避ける設計が各モジュールで採られています（内部で datetime.today() を参照しない、または明示的に target_date を使う等）。
- ネットワーク呼び出しはリトライと指数バックオフ、ステータスコード別の扱いを実装しています（J-Quants / OpenAI）。
- DB 操作は可能な限り冪等に設計（ON CONFLICT や個別 DELETE→INSERT）されています。
- セキュリティ対策: RSS 収集では SSRF 対策（リダイレクト検査、プライベート IP の拒否）、XML パースに defusedxml を使用、レスポンスサイズ上限のチェック等を実装しています。

---

## 参考 / 連絡

ソースコードに各機能の詳細や設計方針コメントを含めています。実運用（本番口座接続や実際の発注）を行う際は、KABUSYS_ENV の設定（paper_trading / live）や十分なテストを行ってください。

不明点や README に追記してほしい内容があれば教えてください。