# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）・ニュース収集・LLMによるニュースセンチメント評価・市場レジーム判定・研究用ファクター計算・監査ログ（発注〜約定トレーサビリティ）などを提供します。

主な用途:
- データパイプライン（株価・財務・カレンダー）の差分取得と品質チェック
- RSS ニュースの収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント / マクロセンチメント評価
- 市場レジーム判定（ETF MA と LLM を組合せ）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 発注〜約定トレーサビリティの監査DB初期化

---

## 機能一覧

- 環境設定管理
  - .env ファイル / OS 環境変数から設定を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN等）

- Data（J-Quants 連携）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS -> raw_news、SSRF 対策・トラッキングパラメータ除去）
  - 監査ログ初期化（signal_events / order_requests / executions テーブル）

- AI（OpenAI／LLM）
  - ニュースセンチメント: news_nlp.score_news (銘柄ごとに ai_scores を作成)
  - 市場レジーム判定: regime_detector.score_regime (ETF 1321 の MA とマクロニュースの LLM スコアを合成)

- Research（研究用ユーティリティ）
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算 / IC 計算 / 統計サマリー
  - zscore 正規化ユーティリティ

- Audit
  - init_audit_schema / init_audit_db：監査用 DuckDB スキーマの冪等初期化

---

## セットアップ手順 (開発 / 実行)

※ Python のバージョンは 3.10+ を想定しています（Union 型 `|` を使用）。

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境を作成・有効化（任意）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate    # Windows
```

3. 必要パッケージをインストール  
（リポジトリに requirements.txt / pyproject.toml がある場合はそちらを使用してください。例として主要依存を記載します）
```bash
pip install duckdb openai defusedxml
```

4. 環境変数（.env）を準備  
プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索します）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env`（最低限必要な項目）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. データベース用ディレクトリを作成（必要であれば）
```bash
mkdir -p data
```

---

## 使い方（主要ユースケース）

以下はPythonインタプリタやスクリプトからの呼び出し例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- 設定アクセス
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続を作成し ETL を実行（日次ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DBの初期化（監査専用DBを作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を利用して監査テーブルへ書き込みが可能
```

- カレンダーヘルパーの利用例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp/regime_detector 等）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視（monitoring）用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment ("development" / "paper_trading" / "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

.env.example を参考に作成してください（リポジトリに存在する場合）。

---

## 注意点 / 設計上の考慮

- look-ahead bias 対策:
  - AI / ETL / 研究用関数は内部で date.today() を直接参照しない設計で、target_date を明示して使用します。
  - J-Quants データ取得では fetched_at を UTC で保存し「いつデータを知り得たか」を明示します。

- 冪等性・トランザクション:
  - ETL の保存関数は ON CONFLICT DO UPDATE による冪等性を確保しています。
  - 一部の初期化関数は transactional オプションを提供します（例: init_audit_schema）。

- 外部呼び出し耐性:
  - J-Quants / OpenAI 呼び出しはリトライ・バックオフ・レート制御を備え、APIエラー時はフェイルセーフを取る設計（多くのケースで 0.0 などの中立値へフォールバック）。

- セキュリティ:
  - RSS 取得で SSRF 対策、XML パースに defusedxml を使用、レスポンスサイズ制限など複数の防御を実装しています。

---

## ディレクトリ構成

リポジトリの主要構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースの LLM センチメント処理
    - regime_detector.py               — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント & 保存ロジック
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL インターフェース再エクスポート
    - news_collector.py                — RSS 収集
    - calendar_management.py           — マーケットカレンダー管理
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore 等）
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum / value / volatility）
    - feature_exploration.py           — 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ の各サブモジュールは相互に依存する部分を最小にし、テスト可能な設計を意識

---

## 開発・テストに関するヒント

- 自動 .env ロードを無効にしたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定します（テストで環境を操作したい場合に有用）。

- OpenAI 呼び出しのテスト:
  - news_nlp と regime_detector 内の _call_openai_api を unittest.mock.patch で差し替える設計になっています。

- DuckDB の executemany 空リスト制約:
  - DuckDB 0.10 系では executemany に空のパラメータリストを渡すと失敗するため、コード中で空チェックを行っています。テスト等でも同様に注意してください。

---

README に書かれている以外の詳細は、各モジュールの docstring を参照してください。追加の使い方・サンプルが必要であれば、どの機能についての例を見たいか教えてください。