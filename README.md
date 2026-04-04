# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得／ETL、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、ファクター計算、監査ログなど、アルゴリズム取引の基盤となる機能を提供します。

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に永続化する ETL パイプライン
- RSS 収集とニュースの前処理、OpenAI（gpt-4o-mini）を用いたニュースセンチメントのバッチスコアリング
- ETF（1321）の MA 乖離とマクロニュースセンチメントを合成した市場レジーム判定
- ファクター（モメンタム、バリュー、ボラティリティ等）計算および特徴量探索ユーティリティ
- 監査（audit）テーブルの初期化と管理（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック、マーケットカレンダー管理、ニュース収集等の補助モジュール

設計上のポイント：
- ルックアヘッドバイアス回避（datetime.today()/date.today() を直接参照しない等）
- 冪等性（保存処理は基本的に ON CONFLICT / DO UPDATE または INSERT … DO NOTHING）
- フォールトトレラントな API 呼び出し（リトライ・バックオフ）
- テスト容易性（OpenAI 呼び出し等をモック可能）

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - 品質チェック（missing / spike / duplicates / date consistency）
  - ニュース収集（RSS 取得・正規化・保存ロジック）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM に投げ、ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースを合成して market_regime に記録
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings クラス: 環境変数管理（.env / .env.local の自動読み込み機能あり）
- audit
  - 監査（signal_events / order_requests / executions）テーブル DDL と初期化ロジック

---

## 前提・依存関係

- Python 3.10+
  - （typing の | 演算子や型注釈の記法を使用しているため）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス:
  - J-Quants API へアクセスするためのリフレッシュトークン
  - OpenAI API（LLM）利用時は OPENAI_API_KEY が必要

requirements.txt がある想定の場合:
```
pip install -r requirements.txt
```
パッケージのローカル開発インストール想定:
```
pip install -e .
```

---

## 環境変数（.env）

自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（優先度: OS env > .env.local > .env）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須／任意キー例（.env に設定してください）:
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants のリフレッシュトークン
- OPENAI_API_KEY（LLM を使う場合は必須）
- KABU_API_PASSWORD（kabuステーション連携用）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN（任意: 通知）
- LINE_USER_ID（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB など。デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定

注意:
- settings.jquants_refresh_token 等は kabusys.config.settings から参照できます。
- 必須変数未設定時は Settings のプロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン／配置
2. Python 仮想環境の作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt や pyproject.toml があればそれに従ってください）
4. .env をプロジェクトルートに作成（.env.example を参考）
5. DuckDB 用フォルダ等が必要であれば作成（settings.duckdb_path の親ディレクトリ等）

---

## 使い方（主要な例）

以下はライブラリを直接呼ぶ簡単なサンプルです。実行前に .env と DuckDB スキーマ（raw_prices など）準備が必要です。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースを LLM でスコアして ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジームを判定して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- ファクター計算（モメンタム等）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- 監査用 DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit を使って監査テーブルへアクセス可能
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

テスト時のヒント:
- OpenAI 呼び出しは内部で _call_openai_api を経由している関数があるため、unittest.mock.patch で差し替えて制御できます（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用の環境設定をプログラム側で行ってください。

---

## ディレクトリ構成（主要ファイル）

※パッケージルートは src/kabusys 以下を想定しています。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数管理、.env 自動読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの集約と OpenAI による銘柄別センチメントスコア付与
    - regime_detector.py     — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・正規化・保存
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査テーブル DDL と初期化ロジック
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai、data、research の下にさらに補助関数・テスト用差し替え可能な内部ユーティリティあり

---

## 注意事項 / 実運用での留意点

- OpenAI 使用時はコストとレイテンシに注意してください。batch サイズやチャンク戦略はニュース処理で既に考慮されていますが、運用環境に合わせて調整してください。
- J-Quants の API レート制限（120 req/min）を守るために RateLimiter を使用しています。並列化するときは注意してください。
- DuckDB のバージョン互換性: executemany の挙動や配列バインドに差があるため、コードでは互換性を考慮していますが、使用する DuckDB バージョンで動作確認してください。
- ルックアヘッドバイアス対策として、関数は内部で現在時刻を直接参照しないように設計されています。バックテストなどで使用する際は target_date を明示的に渡してください。
- ニュース収集は外部サイトの RSS をダウンロードします。SSRF 対策・レスポンスサイズ制限等の防御を実装していますが、運用上のセキュリティポリシーに従ってください。

---

## 開発／テスト

- OpenAI 呼び出しや外部 HTTP コールはモック可能に設計されています（モジュール内の wrapper 関数をパッチする手法を推奨）。
- 自動 .env 読み込みを無効化して、テスト用の環境変数をプログラム側で注入することができます。

---

この README はリポジトリ内のドキュメントを補完するための概要です。各モジュールの詳細（引数仕様や戻り値、例外仕様）はソースコードの docstring を参照してください。必要であれば、各機能ごとのより詳細な使用例や運用ガイドを追加します。