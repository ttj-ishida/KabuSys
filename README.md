# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株を対象としたデータパイプライン、リサーチ、ニュース解析、監査ログ、戦略/実行支援を提供するライブラリ群です。  
本リポジトリは DuckDB を用いたデータレイヤ、J-Quants API クライアント、ニュース収集と LLM を用いたニュース解析・市場レジーム判定、ファクター計算など、アルゴリズムトレーディング基盤に必要な主要機能を含みます。

主な用途:
- 日次 ETL（株価・財務・市場カレンダー）を自動実行してデータベースに保存
- ニュースを収集して LLM によるセンチメント分析を実行（銘柄別 ai_score）
- ETF とマクロニュースを組み合わせて市場レジームを判定
- ファクター計算と研究用ユーティリティ（IC、リターン計算、正規化等）
- 発注・約定までの監査ログ（トレーサビリティ）スキーマ提供
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策・raw_news 保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース NLP（銘柄別センチメントを ai_scores に書き込む: score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュース LLM を合成: score_regime）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索ユーティリティ（forward returns / IC / summary / rank）
- config
  - 環境変数読み込みと設定管理（.env 自動ロード、必須設定の検査）
- audit / execution / strategy / monitoring
  - (骨子) 監査・執行・戦略・監視に関するモジュール構成を含む（監査スキーマ実装済み）

---

## 要件（代表）

- Python 3.10+
- duckdb
- openai
- defusedxml
- (標準ライブラリ以外の依存は環境に応じて追加)

必要なパッケージは setup.py / pyproject.toml（プロジェクトルートに存在する前提）や requirements.txt を参照してください。無い場合は最低限以下をインストールしてください:

pip install duckdb openai defusedxml

---

## セットアップ手順（簡易）

1. リポジトリをクローンする
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .      # パッケージ化されている場合
   - または個別に: pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env`（および `.env.local`）を配置してください。
   - 既存の `.env.example` を参考に必要なキーを設定します（以下参照）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

5. データベースの初期化
   - DuckDB ファイルの親ディレクトリは自動作成されます。設定で指定されたパスに対して接続を作成してください（デフォルト: data/kabusys.duckdb）。

---

## 環境変数（主要）

このライブラリは .env ファイル（プロジェクトルート）または環境変数から設定を読み込みます。主要なキー:

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD
  - kabuステーション等のローカルブローカー API パスワード（必須）
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN
  - Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID
  - Slack チャンネル ID（必須）
- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV
  - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL
  - ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY
  - OpenAI API キー（AI モジュール使用時に必要）

注意:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表的なコード例）

以下は主要機能の呼び出し例です。実運用ではロギングや例外処理、スケジューリングを適切に追加してください。

1) DuckDB 接続の作成と ETL 実行（data.pipeline.run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースのセンチメントスコアを取得して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を使用
print("written:", n_written)
```

3) 市場レジーム判定（1321 + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit_kabusys.duckdb")
# この conn_audit に対して発注／約定ログを保存できるスキーマが作成される
```

5) 研究用ファクター計算の利用例

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
```

---

## よくある注意点 / 設計上のポイント

- ルックアヘッドバイアス対策: モジュールの多くは内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す設計です。バッチやバックテストから利用する際は target_date を明示してください。
- DuckDB の executemany では空リストを投げられない制約を考慮した実装がなされています（空チェックが行われます）。
- OpenAI 呼び出しは JSON Mode を前提にし、レスポンスの検証やリトライ、フォールバック（失敗時は 0.0 を返す）を組み込んでいます。
- NewsCollector は SSRF 対策・受信サイズ制限・XML 防御を実装しています。
- J-Quants クライアントはレート制御（120 req/min）とトークン自動リフレッシュ、リトライを実装しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下に配置されています。主要ファイル例:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - audit (初期化/DBヘルパ)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py

（上記は抜粋。実際のツリーはプロジェクトをご確認ください）

---

## 貢献・拡張ポイント

- 新しいニュースソースの追加（DEFAULT_RSS_SOURCES を拡張）
- 戦略層（strategy）・執行層（execution）・監視（monitoring）の実装拡充
- OpenAI モデルやプロンプトのチューニング
- ETL のスケジューラ（Airflow / cron）連携
- テストスイート（ユニット・統合）と CI 設定の充実

---

## ライセンス・免責

- 本リポジトリに含まれるコードは（ライセンス情報に従って利用してください）。  
- 実際の資金運用に使用する場合は十分なテストとリスク管理を行ってください。外部 API の利用や実取引には十分ご注意ください。

---

質問や README への追加情報の希望（例: 実行スクリプト、CI、より詳細なセットアップ手順など）があれば教えてください。README を拡張します。