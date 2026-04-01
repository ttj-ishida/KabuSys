# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。ETL、ニュース収集・NLPスコアリング、マーケットレジーム判定、ファクター研究、監査ログ（トレーサビリティ）など、量的運用に必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない）
- DuckDB を中心にローカル永続化し、冪等性を重視した保存処理
- 外部 API 呼び出しに対して堅牢なリトライ／バックオフ実装
- API キー等は環境変数 / .env からロード（自動ロード機能あり）

---

目次
- プロジェクト概要
- 機能一覧
- 依存関係
- セットアップ手順
- 必要な環境変数 (.env)
- 使い方（サンプル）
- ディレクトリ構成
- 開発メモ / 設計上の注意

---

## プロジェクト概要

KabuSys は日本株向けに設計されたデータプラットフォーム兼研究／実行ライブラリです。J-Quants API からデータを取得して DuckDB に保存する ETL、RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント（銘柄別）・マクロ判定、株価・財務を使ったファクター計算、監査ログ（シグナル→注文→約定のトレーサビリティ）などを提供します。

---

## 機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save の実装、レート制御・リトライ・トークン更新）
  - market calendar 管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - ニュース収集（RSS の安全な取得、SSRF 防御、前処理、raw_news への保存）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores テーブルへ書込）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースで bull/neutral/bear を判定）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランキング
- config
  - 環境変数読み込み（.env / .env.local 自動ロード）、Settings オブジェクト
- monitoring / execution / strategy / etc.
  - （パッケージの __all__ に含める構成準備あり）

主要な設計目標は「再現性」「堅牢性」「ルックアヘッドバイアス排除」です。

---

## 依存関係（主なもの）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリに依存する部分多数）
- 追加で monitoring（psutil 等）や Slack 通知を行う場合は該当ライブラリが必要です。

（プロジェクトの setup/pyproject に依存関係を明記してください。ここではコードからの推定依存関係を示しています。）

---

## セットアップ手順

1. リポジトリをクローンしてソースフォルダへ移動
   - 例: git clone ... && cd kabusys

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject があればそれに従う）

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成してください。
   - config.Settings は自動的にプロジェクトルートの .env を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます）。

5. DuckDB ファイルや監査 DB の初期化例（任意）
   - Python から:
     - import duckdb
     - from kabusys.config import settings
     - conn = duckdb.connect(str(settings.duckdb_path))
     - from kabusys.data import audit
     - audit.init_audit_schema(conn)

---

## 必要な環境変数（例）

以下は必須またはよく使われる環境変数の一覧です。プロジェクトに .env.example を用意している場合はそれをコピーして編集してください。

- JQUANTS_REFRESH_TOKEN (必須)  
  → J-Quants のリフレッシュトークン（get_id_token のため）
- OPENAI_API_KEY (必須 for AI 機能)  
  → OpenAI API 呼び出しに使用
- KABU_API_PASSWORD (必須 if kabu-api を使う部分が有効な場合)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 if Slack 通知を利用)
- SLACK_CHANNEL_ID (必須 if Slack 通知を利用)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)  
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

注意: configモジュールは .env → .env.local の順で読み込み、OS 環境変数を上書きしません（.env.local は override=True ですが OS 環境変数は保護されます）。

---

## 使い方（主要なサンプル）

以下は Python から主要機能を呼ぶ最小の例です。実運用ではログ設定や例外処理を追加してください。

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアして ai_scores に保存する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数にある場合 api_key を省略可能
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジーム（bull/neutral/bear）を判定して保存する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化（専用 DB に作る場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を監査記録の書き込みに使用
```

- 研究用ファクター計算（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict リスト
```

- ETL 結果の品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## 主要 API の注意点

- OpenAI 呼び出し（news_nlp / regime_detector）は api_key 引数を受け取るか、環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN を利用して id_token を取得します。get_id_token / fetch_* 関数は内部でトークンキャッシュと自動リフレッシュを行います。
- ETL / AI 処理は部分失敗を想定しており、失敗時にはログを残しつつ他の処理を継続する設計です（フェイルセーフ）。
- データ書き込みは可能な限り冪等（ON CONFLICT / DELETE→INSERT）を心がけています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュールの構造（src/kabusys 以下を中心に）:

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
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (存在は __all__ に含むが省略)
  - strategy/, execution/ 等（パッケージ化済み）

上記以外にもユーティリティや将来的なモジュールが配置される想定です。

---

## 開発メモ / 設計上の注意

- ルックアヘッドバイアス対策のため、ターゲット日付は常に明示的に渡すことを推奨します（内部で date.today() を参照しない設計になっています）。
- テスト時に自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとバージョンによって問題があるため、コード内で空チェックを行っています。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用する想定でパースやバリデーションを行っています。API 側の変更やレスポンスの異常に対するフォールバックがありますが、想定外フォーマットはスキップされることがあります。
- news_collector は SSRF や XML-Bomb、巨大レスポンスを防ぐための対策を組み込んでいます（defusedxml、ホスト検査、サイズ上限など）。

---

必要に応じて README を拡張して、実運用用の systemd / cron の設定例、Dockerfile、CI テストフロー、具体的な DB スキーマ定義（DDL）や .env.example を追加してください。質問や追加で含めたい内容があれば教えてください。