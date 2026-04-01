# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）→ DuckDB 保存 → 品質チェック → ファクター計算 → ニュース / LLM を使ったセンチメント評価 → 市場レジーム判定 → 監査ログ（発注/約定トレース）といったワークフローをモジュール化しています。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPXカレンダーを差分取得して DuckDB に保存（冪等保存）
  - 差分取得・バックフィル対応、ページネーション、トークン自動リフレッシュ、レート制御
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue 型で問題を集約して返す
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、SSRF 対策、トラッキングパラメータ除去、記事ID生成、raw_news への保存想定
- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースをまとめ、LLM（gpt-4o-mini）へ投げて銘柄センチメント（ai_scores）を算出
  - タイムウィンドウは前日15:00 JST ～ 当日08:30 JST（UTC に変換して DB と比較）
  - バッチ/リトライ/レスポンスバリデーション実装
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成
  - LLM 呼び出しのフェイルセーフ（失敗時 macro_sentiment=0）
  - market_regime テーブルへ冪等書き込み
- 研究 / ファクター計算
  - Momentum / Volatility / Value 等の定量ファクター計算
  - 将来リターン算出、IC（スピアマンランク相関）、Zスコア正規化等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマ定義と初期化ユーティリティ
  - 発注フローを UUID 連鎖でトレース可能にする DB 初期化関数

---

## 必要条件 / 依存ライブラリ（例）

- Python 3.10+（型注釈に | を使用しているため 3.10 以上を想定）
- 必要な外部パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクトで必要な追加ライブラリやバージョンは requirements.txt を用意して運用してください。

---

## 環境変数（必須/主要）

KabuSys は .env ファイルまたは環境変数を読み込みます（プロジェクトルートに .env/.env.local があれば自動でロード。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD：kabu API パスワード（必須）
- KABU_API_BASE_URL：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN：Slack Bot トークン（必須）
- SLACK_CHANNEL_ID：Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH：デフォルトデータベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH：監視 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT：監視閾値（%）
- KABUSYS_ENV：development / paper_trading / live（デフォルト development）
- LOG_LEVEL：ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime で必要）

例 .env（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: 自動ロードはプロジェクトルート（.git または pyproject.toml のある場所）を基準に行います。

---

## セットアップ手順（開発・実行の一例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（.env をプロジェクトルートに作成）
   - .env に上記の必須変数を記載してください。

4. DuckDB ファイルとデータディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

5. 監査ログ DB 初期化（例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（代表的な API の例）

- DuckDB 接続を作って、ETL を日次実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースセンチメント（ai_scores）を生成する例:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
conn.close()
```
score_news は OPENAI_API_KEY を環境変数で参照します（api_key 引数でも指定可能）。

- 市場レジーム判定を実行する例:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

- 監査ログテーブルを既存 DB に追加する:
```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究用）の例:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
conn.close()
```

---

## 注意点 / 設計上の留意事項

- Look-ahead バイアス防止:
  - 多くの関数は datetime.today()/date.today() を内部で直接参照しない設計で、target_date を明示的に渡すことを想定しています。
  - ETL や研究処理をバックテスト用途に利用する場合は、バックテストの時刻で入手可能なデータのみを DB に事前ロードしてから処理してください。

- OpenAI / J-Quants の API 呼び出しにはコストやレート制限があるため、本番実行時は API キーとレートに注意してください（モジュール内でリトライやレート制御を行っていますが、使用量・課金は運用側で管理してください）。

- ニュース収集では SSRF 対策や受信サイズ制限、XML パースに defusedxml を使用するなどセキュリティ考慮が含まれます。

- DuckDB と executemany の挙動（バージョン依存）を考慮しているコードが含まれます（空配列での executemany を避ける等）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (ETLResult re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージ定義あり、本 README に示されていないがパッケージ __all__ に含まれています)
- strategy/, execution/（パッケージエントリが __all__ にあるもののソースはこの抜粋に含まれていません）

（上記は主要モジュールの抜粋です。実際のリポジトリでは追加のモジュールやスクリプトが存在する可能性があります）

---

## 開発におけるヒント

- テスト時に環境変数の自動読み込みを無効化するには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI への呼び出しは内部関数をテスト用にモックできるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB 接続はテストで ":memory:" を使えるように設計された関数（init_audit_db など）があります。

---

ご不明点や README に追記したい利用シナリオ（例: Docker 化、CI/CD、具体的な運用コマンドなど）があれば教えてください。README をその用途向けに拡張します。