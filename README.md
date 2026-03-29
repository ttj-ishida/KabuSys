# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLPスコアリング、ファクター計算、マーケットレジーム判定、監査ログ（発注〜約定トレーサビリティ）などのユーティリティを提供します。

本ドキュメントはこのリポジトリ内の主要モジュールから README.md 相当の説明を抜粋してまとめたものです。

---

## 概要

KabuSys は以下のような機能を持つモジュール群で構成されています。

- データプラットフォーム（J-Quants からの株価・財務・カレンダー取得、DuckDB への保存）
- ニュース収集（RSS）と前処理（SSRF 対策、URL 正規化）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメントスコアリング）
- 市場レジーム判定（ETF の MA とマクロニュースセンチメントの合成）
- 研究用ツール（ファクター計算、将来リターン、IC、統計要約、Z スコア正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログテーブル（signal → order_request → execution のトレースを可能にする Schema と初期化）

設計上の要点:
- ルックアヘッドバイアスを避けるため、内部で datetime.today() を直接参照しない実装（関数に target_date を明示）。
- DuckDB をデータストアとして利用（軽量かつ分析向け）。
- 外部 API 呼び出しにはリトライ / バックオフ / レート制御を備え安全に実行。
- OpenAI（gpt-4o-mini 等）を利用する NLP 部分は JSON モードでの堅牢なパースとフェイルセーフ（失敗時はスコア 0）を実装。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API との取得／保存／認証ロジック（レート制限・リトライ・キャッシュ付き）
  - pipeline: 日次 ETL（calendar / prices / financials）の差分取得、品質チェック、ETLResult の提供
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・URL 正規化）
  - calendar_management: 市場カレンダー管理と営業日判定ユーティリティ
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - audit: 監査ログ（signal_events / order_requests / executions）テーブル定義と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースを OpenAI で評価し ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime へ書込
- research/
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: forward returns, IC 計算, factor_summary, rank 等

---

## 要件

- Python 3.10+
- 必要なライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は上記を中心に。プロジェクトごとに requirements.txt を用意してください）

---

## 環境変数 / 設定

KabuSys は .env ファイル（プロジェクトルート）または環境変数から設定を読み込みます（自動ロード）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD: kabuステーション等のパスワード（発注系）
  - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- 任意 / デフォルトあり
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで利用）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードの無効化（1 を設定）

注意: Settings オブジェクト（kabusys.config.settings）からこれらにアクセスできます。必須項目が未設定の場合は ValueError が発生します。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトを editable install する場合）pip install -e .

4. .env を作成して必要な環境変数を設定（上記参照）

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

6. DuckDB 接続確認（任意）
   - Python REPL で duckdb.connect("data/kabusys.duckdb") が開けることを確認

---

## 使い方（簡単な例）

ここでは Python スクリプトからライブラリを呼び出す例を示します。各関数は DuckDB 接続や target_date を受け取る設計です（ルックアヘッドバイアス防止のため）。

- 日次 ETL を実行（pipeline.run_daily_etl）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai.news_nlp.score_news）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("書き込んだ銘柄数:", n_written)
```

- レジーム判定（ai.regime_detector.score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成される
```

- research モジュール例（ファクター計算 → 正規化 → IC 計算）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# z-score 正規化したい列の例
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## 注意事項 / 設計上のポイント

- すべての「日付ベース処理」は target_date を引数に受け取り、内部で現在時刻を参照しないようになっています（バックテスト時のルックアヘッドバイアス対策）。
- OpenAI API は JSON mode を利用し、レスポンスの検証を厳密に行ってから DB に書き込みます。API 失敗時はフェイルセーフで 0.0 を使用する等の挙動を取ります。
- J-Quants API との通信はレート制御（120 req/min）・リトライ・トークン自動リフレッシュが組み込まれています。
- news_collector には SSRF 対策（リダイレクト先のホスト検査、プライベート IP 拒否）、受信サイズ制限、XML の安全パーサー（defusedxml）を採用しています。
- DuckDB に書き込む各 save_* 関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識した実装です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: schema / helper ファイルがある想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（ユーティリティ）
  - monitoring/（モニタリング系の実装がある想定）
  - execution/（約定・発注系の実装がある想定）
  - strategy/（戦略実装がある想定）

---

## よくある質問（簡易）

- Q: .env の自動ロードを無効化したい
  - A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

- Q: OpenAI のキーを関数引数で渡したい
  - A: score_news / score_regime 等は api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を参照します。

- Q: DuckDB の path を変えたい
  - A: 環境変数 `DUCKDB_PATH` を設定するか、duckdb.connect() を直接呼び出して任意のファイルを使用してください。

---

もし README に追加したい具体的な例（CLI スクリプト、systemd 定期実行例、Airflow 連携例、requirements.txt の生成など）があればお知らせください。必要に応じて使用方法やサンプルスクリプトを追記します。