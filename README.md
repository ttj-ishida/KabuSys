# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定のトレース）など、システム構築に必要なコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を備えた内部ライブラリ群です。

- J-Quants API を用いたデータ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- RSS ニュース収集とニュースの前処理 / センチメント解析（OpenAI）
- 日次 ETL、データ品質チェック
- ニュースベースの銘柄別 ai_score の作成（ai_scores）
- マクロニュース + ETF MA 乖離に基づく市場レジーム判定
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 監査ログテーブル（signal_events, order_requests, executions）初期化ユーティリティ

設計上のポイント:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を不用意に参照しない設計）
- 冪等性（DB 保存は ON CONFLICT を利用）
- 外部 API 呼び出しはリトライ・バックオフやフェイルセーフを備える

---

## 主な機能一覧

- data.etl.run_daily_etl: 日次 ETL（カレンダー・株価・財務・品質チェック）
- data.pipeline.ETLResult: ETL の実行結果オブジェクト
- data.jquants_client: J-Quants との通信・保存ユーティリティ（fetch / save）
- data.news_collector.fetch_rss: RSS 取得と前処理
- data.calendar_management: JPX カレンダー管理・営業日判定
- data.quality: 品質チェック（欠損・スパイク・重複・日付不整合）
- data.audit.init_audit_db / init_audit_schema: 監査ログテーブル初期化
- ai.news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
- ai.regime_detector.score_regime: マクロ + ETF MA で市場レジームを判定
- research.calc_momentum / calc_volatility / calc_value: ファクター計算
- data.stats.zscore_normalize: Zスコア正規化ユーティリティ

---

## 要件

- Python 3.9+
- 推奨ライブラリ（一例）:
  - duckdb
  - openai（OpenAI の公式 SDK）
  - defusedxml
- 標準ライブラリで多くが実装されていますが、実行環境によって上記パッケージをインストールしてください。

例:
pip install duckdb openai defusedxml

（プロジェクトに requirements.txt を用意する場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境を作成・有効化（例: python -m venv .venv; source .venv/bin/activate）
3. 必要パッケージをインストール
   - 例: pip install -r requirements.txt
   - または: pip install duckdb openai defusedxml
4. 環境変数を設定（またはプロジェクトルートに .env / .env.local を配置）
   - .env の自動ロード:
     - パッケージは .git または pyproject.toml の位置を基準にプロジェクトルートを探索し、`.env` → `.env.local` の順で自動ロードします。
     - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨ファイル構成例（最低限）:
- .env
- data/ (データ格納ディレクトリ)
  - kabusys.duckdb (デフォルト)
  - monitoring.db (SQLite を使用する場合)

---

## 環境変数 (.env) — 例

以下は主要な必須/任意の環境変数例です。実際には .env.example を参照して作成してください。

必須:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- OPENAI_API_KEY=your_openai_api_key

任意（デフォルト値あり）:
- KABUSYS_ENV=development|paper_trading|live  (default: development)
- LOG_LEVEL=INFO|DEBUG|... (default: INFO)
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

注意:
- Settings は kabusys.config.settings 経由で参照できます。
- 必須変数が未設定の場合、Settings のプロパティは ValueError を送出します。

---

## 使い方（クイックスタート）

以下は Python インタラクティブまたはスクリプトから呼ぶ例です。

1) DuckDB 接続を作成（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュース NLP（ai_scores 生成）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定済みであれば api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ用 DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意事項:
- OpenAI を利用する機能は API キー（環境変数 OPENAI_API_KEY も可）を必要とします。key を明示的に渡すことも可能です（関数の api_key 引数）。
- ETL / ニュース / レジーム判定は Look-ahead バイアス対策で、内部的に target_date 未満のデータのみを参照するよう設計されています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定管理（.env 自動読み込みロジック・Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP / OpenAI 統合、ai_scores 書込み
  - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - pipeline.py — ETL パイプライン・run_daily_etl 等
  - etl.py — public ETL 型の再エクスポート
  - news_collector.py — RSS 収集、前処理、raw_news保存
  - calendar_management.py — JPX カレンダー管理、営業日判定
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - quality.py — データ品質チェック
  - audit.py — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（この README はリポジトリ内の主要モジュールに基づいています。詳細は各モジュールの docstring を参照してください。）

---

## 開発・貢献

- テスト時は環境変数読み込みを抑止するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。
- OpenAI 呼び出し等をモックするためにモジュール内のラッパー関数を patch してテスト可能です（コード内にテスト用フックを残しています）。
- 追加のユニットテスト・整備済み requirements.txt、CI 設定、ドキュメント拡張を歓迎します。

---

必要であれば、README にサンプル .env.example、requirements.txt の推奨内容、あるいは各 API の詳細な使用例（入出力例）を追加で作成します。どの情報を優先的に追加しましょうか？