# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを含むモジュール群を提供します。

## 主な特徴
- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得（ページネーション対応・レートリミット・トークン自動更新）
- DuckDB を用いた ETL パイプライン（差分取得、冪等保存、品質チェック）
- ニュース収集（RSS）・前処理・LLM（OpenAI）によるセンチメント解析（銘柄別 ai_score 生成）
- マクロニュース＋ETF（1321）MA乖離からの市場レジーム判定（bull/neutral/bear）
- 研究用モジュール：モメンタム・バリュー・ボラティリティ等のファクター計算と特徴量解析（IC / forward returns 等）
- 監査ログ（signal → order_request → execution）用スキーマと初期化ユーティリティ
- 環境変数 / .env 自動読み込み（プロジェクトルート検出）と設定ラッパー

---

## 機能一覧（モジュール別抜粋）
- kabusys.config
  - .env の自動読み込み（.env, .env.local）と Settings オブジェクトによる環境変数アクセス
- kabusys.data.jquants_client
  - API 呼び出し、レート制御、リトライ、fetch/save の実装
- kabusys.data.pipeline
  - run_daily_etl：カレンダー・株価・財務データの差分ETL + 品質チェック
  - ETLResult：実行結果の構造
- kabusys.data.news_collector
  - RSS 取得、URL 正規化、前処理、raw_news への保存ロジック
- kabusys.ai.news_nlp
  - calc_news_window / score_news：ニュースを銘柄別に集約して OpenAI に投げ、ai_scores テーブルへ書き込み
- kabusys.ai.regime_detector
  - score_regime：ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に保存
- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- kabusys.data.audit
  - 監査ログ用スキーマ作成 / init_audit_db（監査専用DBの初期化）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（PEP 604 の「|」型ヒントを用いているため）
- DuckDB、openai、defusedxml などの依存ライブラリが必要

1. リポジトリをチェックアウト／クローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール（プロジェクトに requirements.txt が無い場合は代表的なライブラリを手動で）
   - pip install duckdb openai defusedxml

   （ローカル開発用にインストールするなら）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます（ただし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須となる主な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id

任意（デフォルトがあるもの）
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|... （デフォルト: INFO）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

注意:
- .env.local は .env の上書き（優先）として読み込まれます。
- OS 環境変数は .env の上書きを防止します（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を使う）。

---

## 使い方（主要なユースケース）

以下はライブラリを直接使う簡単な例です。実行前に環境変数を適切に設定してください。

1) DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（カレンダー、株価、財務、品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメント（銘柄別 ai_scores）を生成
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {count}")
```

4) 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルへ書き込まれます
```

5) 監査ログ用の別 DB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブル・インデックスが作成されます
```

6) 研究用ファクター計算（例: momentum）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# returned: list[dict] with keys like 'code', 'mom_1m', 'ma200_dev', ...
```

注意点:
- OpenAI API 呼び出しには `OPENAI_API_KEY` が必要です。引数で直接 `api_key` を渡すことも可能です。
- ETL / スコアリング系は「ルックアヘッドバイアス防止」を意識して実装されています（内部で date.today() 等に依存しない）。
- DuckDB の executemany に関する互換性注意（コード内で考慮済み）。

---

## よく使う API と挙動メモ

- settings（kabusys.config.settings）
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などで設定値を取得

- data.pipeline.run_daily_etl(conn, target_date, ...)
  - 日次 ETL。ETLResult を返す（品質チェック結果を含む）
  - 各ステップは独立してエラーハンドリングされ、可能な限り処理を継続する

- data.jquants_client.fetch_* / save_*
  - J-Quants からの取得関数と DuckDB への保存関数を提供

- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を対象に銘柄別センチメントを OpenAI により評価し ai_scores に保存

- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離（重み 0.7）とマクロニュースの LLM スコア（重み 0.3）を合成して market_regime に保存

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ参照のため存在想定)
  - strategy/ (戦略関連のためのディレクトリ想定)
  - execution/ (注文実行関連のためのディレクトリ想定)

（上記は主要モジュールの一覧です。実プロジェクトではさらにユーティリティやテストなどが配置される可能性があります。）

---

## 運用上の注意・設計方針（抜粋）
- ルックアヘッドバイアス対策
  - 多くの関数が target_date を引数に取り、内部で現在時刻を参照しないよう設計されています（バックテストに適した設計）。
- 冪等性
  - ETL の保存処理は ON CONFLICT DO UPDATE 等で冪等化されているため、再実行による重複を避けられます。
- フェイルセーフ
  - LLM / 外部 API が失敗した際は致命ではなくフェイルセーフなデフォルト（例: macro_sentiment=0.0）で続行する設計です。
- セキュリティ
  - RSS 収集では SSRF 対策（ホスト検証、リダイレクト検査）、defusedxml による XML パース安全化、受信サイズ上限設定などを実装しています。

---

## さらに
- テスト用に環境変数の自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（パッケージ起動時の .env 自動ロードをスキップします）。
- 実運用での発注処理や Slack 通知連携などは strategy / execution / monitoring パッケージを通じて実装していく想定です。

---

必要であれば、README に含める具体的な .env.example、requirements.txt の候補、あるいは具体的な ETL 実行スクリプト（cron / Airflow 用サンプル）も作成します。どれを追加しますか？