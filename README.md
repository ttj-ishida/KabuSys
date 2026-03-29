# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群（部分実装）。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログなどの機能を提供します。

## 概要
KabuSys は以下の目的を想定したモジュール群です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集し raw_news に保存、銘柄ごとにニュースを集約して LLM（OpenAI）でセンチメント評価するニュース NLP
- ニュースとテクニカル指標を組み合わせて市場レジーム（bull/neutral/bear）を日次判定
- 研究用途のファクター計算・特徴量探索ユーティリティ（モメンタム、バリュー、ボラティリティ、Forward returns、IC 等）
- データ品質チェック、マーケットカレンダー管理、監査（トレース可能な発注／約定ログ）機能

設計上の特徴：
- ルックアヘッドバイアス防止（内部で datetime.today() を不適切に参照しない設計）
- DuckDB を中心としたローカル保存・分析
- OpenAI への呼び出しは明示的な API キー（引数または環境変数）で行う
- 冪等性を重視した DB 保存（ON CONFLICT / INSERT/DELETE の組合せ）

---

## 主な機能一覧
- data:
  - jquants_client: J-Quants からの fetch/save（daily quotes, financials, market calendar, listed info）
  - pipeline: 日次 ETL（run_daily_etl）と各種差分 ETL ジョブ
  - news_collector: RSS 収集・前処理・SSRF 対策付きダウンロード
  - calendar_management: 営業日判定・next/prev/get_trading_days
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査テーブルの初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai:
  - news_nlp.score_news: ニュースを LLM に投げて銘柄ごとの ai_score を ai_scores テーブルへ書き込む
  - regime_detector.score_regime: MA200 とマクロニュースを組合せて市場レジームを判定・market_regime に保存
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 依存関係（代表）
- Python 3.10+ 推奨
- duckdb
- openai
- defusedxml
- （標準ライブラリ：urllib, json, logging, datetime, 等）

例: requirements.txt（参考）
```
duckdb>=0.10
openai>=1.0
defusedxml
```

---

## セットアップ手順

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install -r requirements.txt
   - あるいは個別に:
     - pip install duckdb openai defusedxml

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env`（必要に応じて .env.local）を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD: kabuステーション等の認証（実装によって使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI 呼び出し時の API キー（score_news / score_regime で使用）
   - 省略可能/デフォルト値あり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: INFO 等（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

4. DuckDB 初期スキーマ
   - audit.init_audit_db() 等を呼んで監査 DB を作成できます（例を後述）。

---

## 使い方（簡単な例）

以下は Python REPL からの簡単な呼び出し例です。実行前に環境変数や DuckDB の接続準備をしてください。

- DuckDB 接続を作る（ファイル DB）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（日次パイプライン）を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースをスコアリングして ai_scores に書き込む（OpenAI API キーは環境変数 OPENAI_API_KEY か引数で渡す）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数を参照
print(f"scored {n} symbols")
```

- 市場レジームを判定して market_regime テーブルに書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- 監査 DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# tables created: signal_events, order_requests, executions
```

注意点:
- OpenAI 呼び出しは API の利用料金が発生します。テスト時はモック化（unittest.mock.patch）して呼び出しを差し替えることを推奨します（コード内でもテスト差替えを想定した設計になっています）。
- J-Quants 呼び出しにはレート制限や認証トークンが必要です。get_id_token() でトークンを取得します。

---

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env 例（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## ディレクトリ構成（主要ファイル）
プロジェクトは src/kabusys 配下にモジュールが配置されています。代表的な構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動読み込み）
    - ai/
      - __init__.py
      - news_nlp.py           # ニュース NLP（score_news）
      - regime_detector.py    # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（fetch / save）
      - pipeline.py           # ETL パイプライン（run_daily_etl 等）
      - news_collector.py     # RSS 収集
      - calendar_management.py# カレンダー管理 / 営業日判定
      - quality.py            # データ品質チェック
      - stats.py              # 統計ユーティリティ（zscore_normalize）
      - audit.py              # 監査テーブル定義・初期化
      - etl.py                # ETLResult 再エクスポート
    - research/
      - __init__.py
      - factor_research.py    # calc_momentum / calc_value / calc_volatility
      - feature_exploration.py# calc_forward_returns / calc_ic / factor_summary / rank
    - ai/
      - regime_detector.py
      - news_nlp.py
    - research/
      - (上記)
- pyproject.toml / setup.cfg / README.md（プロジェクトルートに配置想定）

（実際のパッケージ配布では src/kabusys がインストール対象となります）

---

## テスト／開発ヒント
- OpenAI 呼び出しやネットワーク呼び出しはモック化してユニットテストを行ってください。コード中の _call_openai_api / _urlopen などを patch する設計になっています。
- .env 自動ロードは config.py 内で行われます。ユニットテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にできます。
- DuckDB への executemany に関する互換性（空リスト不可など）にコードが配慮しているため、ETL 結果の params が空でないことを確認してから呼ぶよう注意してください（既に実装済み）。

---

必要に応じて README を拡張して、実運用（kabuステーションとの連携、Slack 通知、監視ジョブの cron 設定、CI/CD のセットアップ方法など）に関する手順を追加できます。追加したい内容があれば教えてください。