# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からのデータ ETL、ニュース収集と NLP による銘柄センチメント評価、マーケットレジーム判定、ファクター計算・研究用ユーティリティ、監査ログ（発注→約定のトレース）などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 設定管理
  - .env / 環境変数からの自動ロード（プロジェクトルート検出）
  - `kabusys.config.settings` 経由で値にアクセス

- データパイプライン（ETL）
  - J-Quants API から株価（日足）・財務・市場カレンダーを差分取得
  - DuckDB へ冪等保存（ON CONFLICT を利用）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）

- データユーティリティ
  - カレンダー管理（営業日判定、次/前営業日取得、カレンダー更新ジョブ）
  - ニュース収集（RSS → 前処理 → 記事リスト取得、SSRF 対策・トラッキング除去）
  - J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 監査ログスキーマ初期化（signal / order_request / executions）

- AI / NLP
  - ニュースをまとめて銘柄別センチメント（ai_scores）を生成（gpt-4o-mini を想定）
  - マクロニュース＋ETF（1321）200 日 MA 乖離による市場レジーム判定（bull / neutral / bear）
  - API 呼び出しは JSON Mode を想定、リトライとフェイルセーフ実装あり

- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - z-score 正規化ユーティリティ

---

## 前提・依存関係

- Python 3.10 以上（型ヒントの | 演算子を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）

パッケージ化された環境であれば requirements.txt にこれらを記載してください。最低限のインストール例:

```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

（プロジェクト配布に requirements.txt / pyproject.toml を用意することを推奨します）

---

## 環境変数（主な設定）

以下は本システムで参照する主な環境変数とデフォルト値（該当する場合）です。必須のものは明記します。

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL / jquants_client が使用）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携を行う場合）

- 任意 / デフォルトあり
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールを利用する場合）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト: INFO
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定

自動で .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）からロードします。自動ロードを無効化するには環境変数を設定してください:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

.env の書式はシェル形式を想定しています（export を許容、コメント・クォート対応）。

---

## セットアップ手順（基本）

1. リポジトリをクローンして環境を用意

```bash
git clone <repo_url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -e .       # パッケージとしてインストールする場合
# または必要パッケージを個別にインストール
pip install duckdb openai defusedxml
```

2. 環境変数を設定（.env をプロジェクトルートに作成）

例 (.env):

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

3. DuckDB 用ディレクトリ作成（デフォルトでは data/ を使用）

```bash
mkdir -p data
```

---

## 使い方（代表的な API / 実行例）

以下はライブラリの代表的な呼び出し例です。すべて Python から呼び出します。

- 設定にアクセス

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続を作成して日次 ETL を実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリング（OpenAI API 必須）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn: duckdb connection
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算の利用例

```python
from kabusys.research import calc_momentum, zscore_normalize
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログ DB 初期化（監査専用 DB を作る）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- RSS 収集（ニュース収集モジュールの単体利用）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- AI モジュールを利用する際は OpenAI API キー（環境変数 OPENAI_API_KEY）を設定してください。
- J-Quants の API を利用する際は JQUANTS_REFRESH_TOKEN を必ず設定してください。
- ETL / 保存系関数は DuckDB のスキーマ（テーブル定義）を前提とします。最初にスキーマ初期化を行う仕組み（data.schema 等）を用意することを想定しています（コードベースに含めることを推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと役割の概略です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄別に集約して OpenAI でスコアリングし ai_scores に書き込むロジック
    - regime_detector.py
      - ETF とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py
      - ETL のメイン処理（run_daily_etl 等）
    - jquants_client.py
      - J-Quants API クライアント（認証・取得・保存）
    - news_collector.py
      - RSS 取得と前処理（SSRF 対策・トラッキング除去）
    - calendar_management.py
      - マーケットカレンダーの管理/判定ロジック
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py
      - 汎用統計ユーティリティ（z-score 正規化）
    - audit.py
      - 監査ログテーブル定義・初期化
    - etl.py
      - 公開インターフェース（ETLResult の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリなど
  - ai/regime_detector.py, ai/news_nlp.py — OpenAI 呼び出しはリトライやフォールバックを備え安全性を重視
  - （将来的に strategy/, execution/, monitoring/ モジュールを含め、取引実行パスを実装）

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止のため、各モジュールは内部で date.today() を無闇に参照しないよう設計されています。target_date を明示して呼び出すことを想定しています。
- OpenAI 呼び出しや外部 API は冗長性を考慮してリトライやタイムアウト、失敗時のフェイルセーフ（スコア 0.0 等）を採っています。運用時は API レートやコストに注意してください。
- jquants_client は 120 req/min のレート制御を実装していますが、運用の負荷に応じて適切にチューニングしてください。
- ニュース収集は SSRF 対策（リダイレクト検査、プライベート IP 拒否）を実装していますが、実際の運用では追加の監視を推奨します。
- DuckDB のバージョン特性（executemany の空リスト不可など）を考慮した実装が多く含まれます。DuckDB のバージョン互換性に注意してください。

---

## サポート / 開発メモ

- 単体テストを追加する際は、外部 API 呼び出し（OpenAI / J-Quants / RSS）をモックすることを推奨します。コード内にはテスト用に差し替え可能な内部呼び出し（_call_openai_api など）が用意されています。
- 本 README では主要な API と使用例を示しましたが、モジュール内部の詳細な関数や戻り値の仕様はソースコードの docstring を参照してください。

---

必要であれば README に以下を追加できます:
- 実運用での推奨設定例 (.env.example)
- DuckDB のスキーマ初期化スクリプト例
- CI / テスト実行方法
- strategy / execution のサンプルワークフロー

追加したい項目があれば教えてください。