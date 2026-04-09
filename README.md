# KabuSys

日本株自動売買プラットフォームのコアライブラリ。データETL、ニュースNLP／市場レジーム判定、ファクター計算、監査ログ、J-Quants / kabu API クライアントなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の運用プラットフォーム向けに設計された Python ライブラリ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への ETL
- RSS ニュース収集と OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約（銘柄別 ai_score）
- マクロニュースと ETF（1321）の移動平均乖離を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査（audit）テーブル群の作成・初期化（シグナル→発注→約定のトレーサビリティ）
- data.quality によるデータ品質チェック
- kabuステーション用 API と発注ロジック（実装は別モジュール想定）

設計上、ルックアヘッドバイアスを避けるために内部処理では現在時刻や当日を不用意に参照しないように配慮されています。また、外部API呼び出しはフェイルセーフ（失敗時は中立値で続行）となる箇所が多くあります。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・取得・DuckDB 保存）
  - カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（Z-score 正規化）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI でセンチメント評価 → ai_scores に書込
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書込
- research/
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- 設定管理
  - kabusys.config.settings: .env/.env.local または OS 環境変数から設定を取得（自動ロードあり）

---

## セットアップ手順

前提
- Python 3.10 以上（コードで `X | Y` 型ヒント等を使用しているため）
- 仮想環境の使用を推奨（venv / pyenv など）

例: 仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要な最低パッケージ（プロジェクトに合わせて requirements.txt を用意してください）
pip install duckdb openai defusedxml
# 自分のプロジェクトとしてローカル editable インストール（pyproject.toml がある場合）
pip install -e .
```

環境変数・.env
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` を自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
- 読み込み順序（優先度）: OS 環境変数 > .env.local > .env

主要な環境変数（一例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- PAPER_FILL_MODE: paper_trading 用モック約定挙動（instant/partial/never/reject）
- KABUSYS_ENV: development|paper_trading|live
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

サンプル .env（プロジェクトルート）
```env
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は主要な API の呼び出し例です。実運用ではスクリプトやジョブスケジューラ（cron / systemd timer など）から呼び出します。

1) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は pathlib.Path を返す
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を明示可能
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）を評価して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 19))
print("書き込み銘柄数:", n_written)
```
- OpenAI API キーを引数で渡すことも可能: score_news(conn, date, api_key="sk-...")

3) 市場レジーム判定を実行して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
n = score_regime(conn, target_date=date(2026, 3, 19))
```

4) 監査ログスキーマの初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# または既存接続に対して init_audit_schema(conn)
```

5) カレンダー・営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

6) 研究系ユーティリティ
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
records = calc_momentum(conn, target_date=date(2026,3,19))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意:
- OpenAI 呼び出しを行う関数は API の失敗時にスコアを中立（0.0 等）にフォールバックする設計です（フェイルセーフ）。
- 多くの関数は "target_date" を明示的に受け取り、内部で date.today() を直接使わないことでルックアヘッドバイアスを軽減しています。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/ 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュースNLP（score_news）
    - regime_detector.py   # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - jquants_client.py    # J-Quants API クライアント（fetch / save）
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py             # 監査ログスキーマ初期化
    - etl.py               # ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py   # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
  - ai/ (上記)
  - research/ (上記)

各モジュールは docstring と詳細な設計ノートを持ち、関数の引数／戻り値／副作用（DB書込など）が明記されています。

---

## 注意事項 / 運用上のポイント

- 必須の外部サービス:
  - J-Quants API（JQUANTS_REFRESH_TOKEN）
  - OpenAI（OPENAI_API_KEY） — news_nlp, regime_detector を使う場合
  - kabuステーション（KABU_API_PASSWORD） — 発注連携を実装する場合
- DB: デフォルトで DuckDB を使用しています。監査用 DB は分離して運用することを推奨します。
- 自動 .env ロードはプロジェクトルートを .git または pyproject.toml で探索します。CI やテストで自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API レート制限、リトライ、指数バックオフ等は jquants_client / ai モジュール内で考慮されていますが、本番運用では更に監視・アラートを組み合わせてください。
- DuckDB バージョンや SQL 方言差異に注意（プロジェクト内では互換性を考慮した実装あり）。

---

もし README に追加してほしいサンプルスクリプト（ETL cron 用やデバッグ用 CLI）、.env.example のテンプレート、または依存関係（requirements.txt）の生成が必要であれば教えてください。