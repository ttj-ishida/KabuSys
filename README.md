# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群（KabuSys）。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株データの取得・品質チェック・特徴量生成・AI ベースのニュースセンチメント評価・市場レジーム判定・監査ログ管理を目的とした内部ライブラリです。  
主に下記用途を想定しています。

- J-Quants API からの日次データ ETL（株価・財務・市場カレンダー）
- RSS からのニュース収集と記事前処理
- OpenAI を利用したニュースセンチメント（銘柄別）およびマクロセンチメントの評価
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算、統計ユーティリティ
- 監査ログ（シグナル → 発注 → 約定）の DuckDB スキーマ初期化と管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、ルックアヘッドバイアスを防ぐために date パラメータを明示的に渡すことを前提にしており、本番発注 API には依存しない研究・ETL 層と運用層のライブラリです。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants クライアント（rate-limit / retry / token refresh 対応）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース処理
  - RSS 取得と前処理（SSRF 対策、トラッキングパラメータ除去）
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
- AI（OpenAI）連携
  - news_nlp（gpt-4o-mini を想定）で銘柄群のスコア化
  - regime_detector で ETF(1321)の MA とマクロニュースの混合で市場レジーム判定
- 研究/ファクター
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（Audit）
  - init_audit_db / init_audit_schema による監査用 DuckDB 初期化
- 設定管理
  - 環境変数および .env 自動読み込み（プロジェクトルート検出、.env.local 上書き）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に `X | None` を使用）
- 仮想環境の利用を推奨

例:

1. リポジトリをクローン（またはソースを配置）
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）
4. パッケージをローカルで開発インストール（任意）
   - pip install -e .

環境変数／.env:
- プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（OS 環境変数が優先されます）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨 / 必要な環境変数（一部）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で必要）
- KABU_API_PASSWORD : kabu API 用パスワード（必要な場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（任意）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : development | paper_trading | live
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続と ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env や環境変数から読み込まれます
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL（target_date を指定しないと today が使われます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアの実行（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None は環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルに作る場合
audit_conn = init_audit_db(settings.duckdb_path)  # ここでは同じ DuckDB を利用する例
```

5) 研究用ユーティリティ（ファクター計算例）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は [{"date": ..., "code": "...", "mom_1m": ..., "ma200_dev": ...}, ...]
```

注意事項:
- news_nlp / regime_detector は OpenAI にリクエストするため API キーと利用制限（料金）が発生します。
- ETL / API 呼び出し系はリトライ・レート制御を備えていますが、API 利用規約を遵守してください。
- 各関数はルックアヘッド（未来データ利用）を避ける設計になっているため、target_date を正しく指定してください。

---

## ディレクトリ構成

主要ファイル・モジュールの一覧（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py              — 環境変数・.env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースの集約／OpenAI でのセンチメント評価 -> ai_scores 書込
    - regime_detector.py   — ETF MA とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch / save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult 再エクスポート
    - news_collector.py    — RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py — 市場カレンダーの判定・更新ロジック
    - quality.py           — データ品質チェック
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - audit.py             — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py   — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/, data/, research/ ... のほか、strategy / execution / monitoring 等のパッケージが __all__ に含まれる想定（各責務に応じて実装）

（コードベース全体は src/kabusys 以下に細かく機能分割されています。README では主要なモジュールのみ抜粋しています。）

---

## 動作上の注意・設計ポイント

- .env 自動ロード:
  - プロジェクトルートは現在ファイル位置から親を遡って `.git` もしくは `pyproject.toml` を探して決定します。見つからない場合は自動ロードをスキップします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロード停止: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し:
  - gpt-4o-mini（定義上）を想定。API 応答のパースに失敗した場合はフェールセーフで中立スコア（0.0）を採用する設計です。
- J-Quants クライアント:
  - 固定間隔レート制限（120 req/min）とリトライ、401 時のトークン自動リフレッシュを実装しています。
- DuckDB:
  - デフォルトの DB パスは data/kabusys.duckdb。監査 DB は init_audit_db で初期化できます。
- 安全性:
  - news_collector は SSRF 対策、XML 攻撃対策（defusedxml）、レスポンスサイズ上限などを実施しています。

---

## 貢献・拡張

- 新しい ETL 対象・API を追加する場合は `kabusys.data.jquants_client` のパターンに従って fetch/save を実装してください（retry・rate-limit・id_token 管理を考慮）。
- OpenAI のモデルやプロンプトは各モジュール内の定数で管理されているため、要件に応じて変更可能です。
- 単体テストでは env 自動ロードの影響を避けるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うか、config の `settings` をモックしてください。

---

以上が README の概要です。必要であれば以下を追加できます：
- 具体的な .env.example ファイル
- CI / テスト実行手順（pytest 例）
- 詳細なスキーマ（DDL）一覧（audit 等のフル DDL はコード内に記載済み）
- サンプルワークフロー（cron や Airflow の DAG）