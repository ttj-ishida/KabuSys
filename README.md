# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ集合です。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、ファクター/リサーチユーティリティ、監査ログ（発注〜約定トレーサビリティ）など、投資戦略運用に必要な基盤機能を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を主要な分析データストアとして利用
- API 呼び出しはリトライ・バックオフ・レート制御を行いフェイルセーフ設計
- 冪等（idempotent）な DB 保存処理

---

## 機能一覧

- 設定管理
  - .env / 環境変数読み込み（自動ロードを環境変数で無効化可）
  - 必須設定の取得ヘルパー（`kabusys.config.settings`）

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（レート制御・トークン自動リフレッシュ・ページネーション対応）
  - ETL パイプライン（株価・財務・市場カレンダーの差分取得と保存）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS -> raw_news、SSRF 対策、トラッキング除去）
  - 監査ログ（signal / order_request / executions テーブル、監査 DB 初期化ユーティリティ）

- AI（kabusys.ai）
  - ニュースのセンチメント付与（OpenAI を用いたバッチスコアリング）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM スコアの合成）

- Research（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Z スコア正規化ユーティリティ（kabusys.data.stats と共有）

- ユーティリティ
  - DuckDB 接続ベースで動く各種関数群
  - OpenAI クライアント呼び出し用の抽象化（テストで差し替えやすい設計）

---

## 前提・依存

- Python 3.10 以上（typing の newer syntax を使用）
- 必要なライブラリ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, datetime, json, logging など

インストール例（最低限のパッケージ）:
```bash
python -m pip install duckdb openai defusedxml
# 開発・パッケージ化されている場合:
pip install -e .
```

（実プロジェクトでは requirements.txt / pyproject.toml に合わせてインストールしてください）

---

## 環境変数 / .env

kabusys は .env ファイル（プロジェクトルートの .git または pyproject.toml を基準に自動読み込み）または OS 環境変数から設定を読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（ETL に必須）
- SLACK_BOT_TOKEN        : Slack 通知に使う Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID       : Slack 送信先チャンネル ID（必要に応じて）
- KABU_API_PASSWORD      : kabu ステーション API のパスワード（実行系で利用）
- OPENAI_API_KEY         : OpenAI 呼び出しに必要（AI モジュールを使う場合）

その他（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

kabusys.config.settings 経由で値にアクセスできます（必須変数は未設定時に ValueError を送出します）。

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン
2. Python 環境を作成・有効化（venv / pyenv 等を推奨）
3. 依存パッケージをインストール
   - 例: pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml
4. プロジェクトルートに .env を作成して必要な環境変数を設定
5. DuckDB ファイルや監査 DB の保存先ディレクトリを作成（必要なら）
6. 必要に応じて監査 DB を初期化:
   - Python から: `kabusys.data.audit.init_audit_db("data/audit.duckdb")`

---

## 使い方（代表的な API）

以下は簡単な利用例です。実運用ではログ設定や例外処理を追加してください。

- DuckDB 接続を作る（ファイル or ":memory:"）:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコア付与（OpenAI API キーが必要）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化（監査専用 DB）:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- ファクター / リサーチユーティリティ:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)            # モメンタム
val = calc_value(conn, d)              # バリュー
vol = calc_volatility(conn, d)         # ボラティリティ
fwd = calc_forward_returns(conn, d)    # 将来リターン
# IC の計算はレコード結合後に利用
```

- 市場カレンダー関係ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
is_trading_day(conn, date(2026, 3, 20))
next_trading_day(conn, date(2026, 3, 20))
get_trading_days(conn, date(2026, 3, 1), date(2026, 3, 31))
```

- J-Quants 生データ取得（必要に応じてテストや確認で使う）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
quotes = fetch_daily_quotes(id_token=token, date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
```

---

## 実装上の注意点・テスト用フック

- 自動で .env を読み込む処理は、テスト時に副作用を避けるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- OpenAI の呼び出しは内部関数 `_call_openai_api` を通じて行われており、ユニットテストでは `unittest.mock.patch` で置き換えて API 呼び出しをモックできます。
- DuckDB の executemany に関する注意（モジュール内に空パラメータでの問題対応あり）。
- ETL / AI モジュールは API 失敗時に例外で即停止させずフォールバックや部分スキップを行う設計です（ロギングで検知）。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP / OpenAI スコアリング
    - regime_detector.py              — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント & 保存関数
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL の公開型再エクスポート（ETLResult）
    - calendar_management.py          — 市場カレンダー管理 / 営業日ロジック
    - news_collector.py               — RSS ニュース収集（SSRF 対策等）
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（z-score 等）
    - audit.py                        — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py              — ファクター計算（momentum, value, volatility）
    - feature_exploration.py          — 将来リターン, IC, summary 等
  - research/（その他ユーティリティは上記参照）

---

## ログ・モード

- 環境変数 `KABUSYS_ENV` により動作モードを切替できます（development / paper_trading / live）。
- `LOG_LEVEL` によりログレベルを制御（デフォルト INFO）。

---

## よくあるユースケース

- 定期バッチ（Cron や Airflow）で毎朝 run_daily_etl を実行してデータ基盤を更新
- 深夜に calendar_update_job を走らせて市場カレンダーを最新化
- 朝に score_news を実行して銘柄別 AI スコアを生成、strategy 層でシグナル生成に利用
- モデル検証・リサーチで calc_momentum / calc_value / calc_volatility を用いたファクター調査
- 発注系では監査 DB（init_audit_db）で signal→order→execution のトレーサビリティを保持

---

必要であれば、README に含めるサンプル .env.example や、より詳細な運用手順（Airflow / systemd / docker-compose での運用例）、テストの実行方法、CI 設定例なども追加できます。どの内容を優先して追記しますか？