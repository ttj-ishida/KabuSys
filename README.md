# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL、ニュース収集 & NLP、研究用ファクター計算、監査ログ、監視・設定管理などを含むモジュール群を提供します。

主な想定用途：
- J-Quants からのデータ収集（株価・財務・市場カレンダー）
- ニュースの収集・LLM による銘柄センチメント付与
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（研究/バックテスト用）
- 発注・約定の監査ログスキーマ初期化
- データ品質チェック（ETL 後の自動検査）

バージョン: 0.1.0

---

## 機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得メソッド (kabusys.config.settings)
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から株価・財務・カレンダーを差分取得
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - run_daily_etl：日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存（SSRF/サイズ制限/トラッキング除去）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日MA乖離 + マクロニュース（LLM）で日次レジーム判定
- 研究用ツール（kabusys.research）
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
- その他ユーティリティ
  - DuckDB 用スキーマ初期化、ETL 結果クラス、設定ラッパー

---

## 必要条件 / 依存関係

- Python 3.10 以上（PEP 604 型注釈の使用のため）
- 必要な（主な）サードパーティライブラリ:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ（urllib, logging, datetime, json 等）

（プロジェクトに requirements.txt がない場合は適宜作成してください。例）
pip install duckdb openai defusedxml

---

## 環境変数（主要）

kabusys.config.Settings で参照される主な環境変数：

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- kabu ステーション（発注 API）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時 http://localhost:18080/kabusapi)
- OpenAI / NLP
  - OPENAI_API_KEY — OpenAI API キー（score_news/score_regime 呼び出し時にも引数で上書き可）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB パス・監視用フラグ
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, など
- 実行環境 / ログ
  - KABUSYS_ENV = development | paper_trading | live (デフォルト development)
  - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL

自動 .env ロード：
- プロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local を自動で読み込みます（OS 環境変数優先）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml がある場合はそれに従ってください）

3. 環境変数を用意
   - プロジェクトルートに .env を作成（.env.example を参考にする想定）
   - 最低限設定するもの：
     - JQUANTS_REFRESH_TOKEN=
     - OPENAI_API_KEY=
     - KABU_API_PASSWORD=

4. データフォルダ作成（デフォルトパスを使用する場合）
   - mkdir -p data

5. DuckDB 接続（初期化）
   - python REPL / スクリプト内で duckdb.connect(str(settings.duckdb_path)) を使って接続できます

---

## 使い方（主要な例）

以下はライブラリ API を呼ぶ簡単な例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定してください。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント付与（OpenAI を使用）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DuckDB ファイルまたは :memory:）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- ETL ユーティリティ（個別ジョブ呼び出し）

run_prices_etl, run_financials_etl, run_calendar_etl などを直接呼べます（kabusys.data.pipeline モジュール参照）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋して説明）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（OpenAI で銘柄別スコア付与）
    - regime_detector.py   — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult 再エクスポート
    - news_collector.py    — RSS ニュース収集（SSRF とサイズ対策あり）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py           — データ品質チェック（欠損・スパイク・重複・日付）
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - audit.py             — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py   — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — 将来リターン / IC / summary utilities
  - ai、data、research はそれぞれの責務で分離されています（API 呼び出しの分離やルックアヘッドバイアス対策に配慮）。

---

## 設計上の注意点 / 運用ノウハウ

- ルックアヘッドバイアス対策
  - 多くの関数は date 引数を明示的に受け取り、datetime.today()/date.today() を内部で直接参照しないように設計されています。バックテスト時は明示的に過去日付を与えてください。
- 冪等性
  - J-Quants 保存・ニュース保存・ai_scores 書き込み等は可能な限り冪等化（ON CONFLICT や記事 ID のハッシュ）されています。
- OpenAI 呼び出し
  - トークンは OPENAI_API_KEY を使用。API 呼び出しはリトライやバックオフを含みますが、レスポンスパース失敗等ではフォールバック値（0.0）に落とす設計です。
- 自動 .env ロード
  - プロジェクトルートを基準に .env/.env.local を自動読み込みします。テスト時や特殊な実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを止めることができます。
- DuckDB の executemany
  - 一部の関数は DuckDB の挙動（executemany に空リストを渡せない等）に合わせた実装になっています。

---

## トラブルシューティング

- 必須環境変数未設定 → ValueError が発生
  - settings.jquants_refresh_token や settings.kabu_api_password などの必須フィールドは取得時に例外を投げます。.env を作成して設定してください。
- OpenAI 呼び出し失敗
  - ネットワーク / 429 / 5xx はリトライしますが、最終的にはログに WARN を出してフォールバック（0.0）します。APIキーやクォータを確認してください。
- DuckDB 関連エラー
  - テーブル未作成時にクエリが失敗するケースがあります。必要に応じてスキーマ初期化や audit.init_audit_schema を実行してください。

---

## ライセンス / 貢献

- 本 README はプロジェクトのコードベースから生成されたドキュメントに基づき作成されています。実装や仕様変更に伴い README を更新してください。

---

必要があれば、セットアップの手順をスクリプト化したサンプル（requirements.txt / docker-compose / makefile）や、よく使う CLI スクリプト（etl_runner, news_scanner など）のテンプレートも作成します。どの形式で追加ドキュメントが欲しいか教えてください。