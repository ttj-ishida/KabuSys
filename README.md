# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ（取引トレーサビリティ）など、量的運用・リサーチに必要な機能群を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主なAPI例）
- ディレクトリ構成
- 環境変数（.env）サンプル
- ライセンス・注意事項

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群をまとめた Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- DuckDB を用いたローカルデータ保存・品質チェック
- RSS によるニュース収集と前処理／NLP（OpenAI）による銘柄別センチメント算出
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究支援ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ・初期化ユーティリティ
- マーケットカレンダー管理（営業日判定、次/前営業日取得）

設計上の特徴として、ルックアヘッドバイアス防止、冪等性（ETL / 保存処理）、APIリトライ・バックオフ、リソース制限（RSSの最大読み込み等）等を考慮しています。

---

## 機能一覧

主要機能（モジュール別）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）と Settings からの設定アクセス
- kabusys.data.jquants_client
  - J-Quants API とのやり取り（取得・保存・ページネーション・トークンリフレッシュ・レート制御）
  - save_* 系で DuckDB へ冪等保存
- kabusys.data.pipeline
  - run_daily_etl：カレンダー、株価、財務の差分ETL と品質チェックを連結した日次パイプライン
  - 個別 ETL ヘルパー（run_prices_etl, run_financials_etl, run_calendar_etl）
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合などの品質チェック
- kabusys.data.news_collector
  - RSS 収集、URL 正規化、前処理、raw_news への保存（冪等）
  - SSRF 対策、受信サイズ制限、gzip 解凍対策などセキュアな実装
- kabusys.ai.news_nlp / kabusys.ai.regime_detector
  - gpt-4o-mini を用いた銘柄別ニュースセンチメント算出（score_news）
  - ETF（1321）の MA 乖離 + マクロニュースセンチメントを合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・フォールバック（失敗時スコア = 0）
- kabusys.research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns, IC, ranking, summary）
- kabusys.data.audit
  - 監査ログ用の DDL / インデックス定義と初期化（init_audit_schema / init_audit_db）
- ユーティリティ
  - zscore_normalize、calendar 関連（is_trading_day, next_trading_day, get_trading_days）など

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。

2. 仮想環境作成（任意）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストールします（最低限）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実運用ではさらにロギング設定や Slack, requests 等が必要な場合があります。package 配布用に requirements.txt を用意している場合はそちらを使用してください。

4. パッケージを開発モードでインストール（リポジトリルートに pyproject.toml がある想定）:
   ```bash
   pip install -e .
   ```

5. 環境変数を設定します（.env を利用するのが簡単です）。自動ロードはデフォルトで有効です（プロジェクトルートに .env を置く）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 環境変数（代表）

必須（Settings._require により未設定だと例外）:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション等の API パスワード（本パッケージが参照）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：通知対象の Slack チャンネル ID

OpenAI 関連（必須ではないが AI機能利用時に必要）:
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime 呼び出しで省略時に参照）

データベースパス（任意。デフォルト値あり）:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）

ログ設定など:
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行われます。読み込み順は OS 環境変数 > .env.local > .env（.env.local は .env を上書き）です。

例 .env は下の章を参照してください。

---

## 使い方（主な例）

以下は代表的な使い方サンプルです。実際にはエラーハンドリング・ログ設定を適宜追加してください。

1) DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを算出する（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20))
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定を実行する（1321 の MA とマクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は必要なテーブル・インデックスを作成し接続を返します
```

5) RSS を取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
# momentum は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

各関数の詳細な挙動（時間ウィンドウ、フォールバック動作、例外の投げ方など）はモジュールの docstring に記載されています。

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP / score_news
    - regime_detector.py     # 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存関数
    - pipeline.py            # ETL パイプライン（run_daily_etl など）
    - quality.py             # データ品質チェック
    - news_collector.py      # RSS ニュース収集
    - calendar_management.py # マーケットカレンダー管理（営業日判定等）
    - audit.py               # 監査ログスキーマ / 初期化
    - etl.py                 # ETL インターフェース再エクスポート
    - stats.py               # 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py     # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py # forward returns, IC, rank, summary
  - monitoring/               # （サンプルとして監視系の実装想定）
  - strategy/                 # （戦略/シグナル生成用のモジュール想定）
  - execution/                # （発注・ブローカー連携のモジュール想定）

（各ファイルは docstring に詳細が書かれており、設計方針や API 仕様が明記されています）

---

## .env サンプル

プロジェクトルートに .env を作成すると自動で読み込まれます（必要なら .env.local を使って上書き）。

例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込みを無効化したい場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 注意事項

- OpenAI / J-Quants の API キー・トークンは機密情報です。Git にコミットしないでください。
- DuckDB のスキーマやテーブル名はコード中に定義されています。運用前にバックアップ / マイグレーション計画を検討してください。
- 実際の売買執行（live モード）は十分な安全対策を行った上で実行してください（テストは paper_trading で行う等）。
- news_collector は外部ネットワークにアクセスします。SSRF 対策等は組み込まれていますが、運用環境のネットワークポリシーにも注意してください。

---

もし README の拡張（例: CI/CD、詳細なスキーマ、追加のサンプルスクリプト、requirements.txt 生成など）をご希望であれば、用途に合わせて追記します。