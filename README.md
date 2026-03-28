# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（部分実装）

簡潔な説明：
- 市場データの ETL、ニュース収集・NLP スコアリング、LLM を用いた市場レジーム判定、研究用ファクター計算、監査ログ（オーディット）機能などを提供するモジュール群です。
- DuckDB を主要なローカルデータストアとして利用し、J-Quants / RSS / OpenAI（gpt-4o-mini）を外部データソースとして扱います。

---

目次
- プロジェクト概要
- 機能一覧
- 要件（依存）
- セットアップ手順
- 環境変数
- 使い方（コード例）
- ディレクトリ構成
- 補足・運用上の注意

---

## プロジェクト概要

KabuSys は、日本株向けのデータプラットフォームと研究／自動売買パイプラインを構成するための内部ライブラリ群です。本リポジトリに含まれる主な機能は以下の通りです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への idempotent 保存
- RSS ニュース収集（SSRF 対策・前処理・重複防止）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント / マクロセンチメント評価（JSON Mode）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / execution）スキーマの初期化と管理

設計方針の大枠：
- ルックアヘッドバイアスを避ける（内部で date.today() 等の非決定的参照を避ける設計）
- DuckDB を用いたローカル ETL / 研究ワークフロー
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える

---

## 機能一覧

主な公開 API（モジュール別）
- kabusys.config.settings
  - 環境変数を集約してアクセス
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult データクラス
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（J-Quants トークン管理）
- kabusys.data.news_collector
  - fetch_rss / preprocess_text / ニュースID生成等
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- kabusys.data.audit
  - init_audit_db(path) / init_audit_schema(conn)

その他、calendar_management（営業日ロジック）など多くのユーティリティがあります。

---

## 要件（依存）

必須（主要）：
- Python 3.10 以上（| 型注釈や match なしでも 3.10 の構文を使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

推奨（環境に応じて）：
- pip 等のパッケージ管理環境

インストール例：
```bash
python -m pip install "duckdb>=0.7" "openai>=1.0" "defusedxml"
```
（実際のバージョンはプロジェクト方針に合わせて固定してください）

---

## セットアップ手順

1. ソースをクローン / 取得
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリのインストール
   ```bash
   pip install -e ".[dev]"     # もし setup/pyproject に extras があれば
   # あるいは個別に
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成してください（.env.example を参考にする運用を想定）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須: J-Quants リフレッシュトークン）
     - OPENAI_API_KEY（OpenAI API キー）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 自動で .env を読み込む仕組みがあります（kabusys.config）が、テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. DuckDB 初期化（監査用 DB 等）
   Python REPL から:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # もしくは init_audit_schema(conn) を既存 conn に対して実行
   ```

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（gpt-4o-mini を利用するために必要）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルト duckdb ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するには 1 を設定

kabusys.config.Settings を通じてこれらにアクセスできます。

---

## 使い方（簡単なコード例）

以下はいくつかの代表的な使い方例です。

1) DuckDB 接続を作り ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
print("scored:", n_written)
```

3) 市場レジーム評価
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn に対して発注・約定ログを挿入できるスキーマが作成されます
```

---

## 注意点 / 運用上のポイント

- ルックアヘッドバイアス回避: 多くの関数（news scoring, regime scoring, ETL 等）は内部で date.today() を無暗に参照せず、target_date を明示的に受け取る設計です。バックテストや再現性のため、target_date を明示して利用してください。
- OpenAI 呼び出し: API のレートやエラーを考慮したリトライ・フォールバックが組み込まれていますが、APIキーや利用ポリシーに注意して運用してください。API の請求に注意。
- J-Quants API: rate-limit（120 req/min）に従う実装になっています。認証トークンの管理は jquants_client による自動リフレッシュで行われます。
- ニュース収集: SSRF 対策・受信サイズ制限・トラッキングパラメータ除去等の安全処理が組み込まれていますが、外部ソースの信頼性には注意してください。
- DuckDB の executemany は空引数を受け付けないバージョンの挙動を考慮している箇所があります（実装済み注意）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。CI やテスト環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 jquants_client 等のクライアントコード)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (READMEで言及されているがコードベースに合わせて追加のモジュール有り得る)
- execution/, strategy/, monitoring/（パッケージ公開変数にあるが本リポジトリの断片で存在する場合あり）

（上記はソース中に実装されている主要ファイルの一覧です。実際のリポジトリではテスト / docs / scripts 等が追加される場合があります。）

---

## 貢献 / 開発

- コードの追加・修正はまずローカル環境でユニットテストを作成・通すことを推奨します。
- 設定は .env.example を置き、秘密情報は直接コミットしないでください。
- 外部 API のモック化（OpenAI / J-Quants / RSS）を行い、ネットワークに依存しないテストを作成してください（既存コード内にモック差し替えを想定した設計があります）。

---

その他の詳細（例: SQL スキーマ、プロンプト内容、リトライポリシー、設計ノート）は各モジュールの docstring を参照してください。README に書かれていない運用上の注意や内部仕様はソース内コメントに多数記載されています。