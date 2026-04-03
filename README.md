# KabuSys

日本株のデータ取得・解析・自動売買を支援するライブラリ／基盤コンポーネント群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定のトレース）、研究用ファクター計算などを提供します。

主な設計方針：
- ルックアヘッドバイアスに配慮（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB をデータ層に使用し、ETL は冪等に保存
- 外部 API 呼び出し（J-Quants / OpenAI 等）はリトライやレート制御を備える
- テスト容易性のため依存注入やモック差し替えポイントを用意

---

## 機能一覧

- データ ETL（kabusys.data.pipeline）
  - J-Quants からの差分取得（株価日足 / 財務 / カレンダー）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - run_daily_etl による一括 ETL 実行

- ニュース収集・NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS フィードからの収集（SSRF 対策・トラッキング除去・最大サイズ制限）
  - OpenAI を用いた銘柄別ニュースセンチメントの算出（ai_scores テーブルへ保存用）
  - バッチ・チャンク処理、リトライ、レスポンスバリデーション

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で判定
  - LLM 呼び出しはリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）

- 研究・ファクター計算（kabusys.research）
  - Momentum / Volatility / Value ファクター、将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査テーブル初期化ユーティリティ
  - init_audit_db により監査用 DuckDB の初期化

- J-Quants クライアント（kabusys.data.jquants_client）
  - API レート制御・リトライ・トークン更新・ページネーション対応
  - raw データを DuckDB に冪等保存する save_* 関数群

---

## 要求環境 / 依存パッケージ

- Python >= 3.10（型注釈で | を使用）
- 主な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他：標準ライブラリ（urllib, json, datetime 等）

（実際に利用する際は requirements.txt を用意して pip install してください。）

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. リポジトリルートに .env を配置（自動ロードあり。プロジェクトルートは .git または pyproject.toml を基準に検出）
   - 自動ロードを無効にする：環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
   - 省略時は defaults が利用される変数:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / など

   .env の自動読み込みロジックについて：
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
   - プロジェクトルートを .git または pyproject.toml で特定。見つからない場合は自動ロードをスキップ。

例: .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

# ファイル DB を使用する場合
db_path = str(settings.duckdb_path)  # 設定から取得
conn = duckdb.connect(db_path)

# メモリ DB を使う場合
# conn = duckdb.connect(":memory:")
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアの生成（OpenAI API キーは環境変数または api_key 引数で渡す）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# ai_scores テーブルへ銘柄別センチメントを書き込む
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"score_news wrote {written} codes")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

# market_regime テーブルへ書き込む
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- J-Quants から直接データを取得（テストや単発取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

# トークンは settings.jquants_refresh_token を用いて取得されます
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

注意点：
- OpenAI 呼び出しでは gpt-4o-mini を利用（JSON mode）しています。レスポンスのバリデーションとリトライを行いますが、API の変化に注意してください。
- ETL / API 呼び出しはネットワーク・API エラーに対してリトライ・フェイルセーフ設計です。必要に応じてログを確認してください。

---

## 設定項目（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news/score_regime 等で使用）
- KABU_API_PASSWORD — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする（任意）

設定取得は kabusys.config.settings 経由でアクセスできます：
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch_*, save_*）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS 取得・正規化・保存
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ初期化（init_audit_schema / init_audit_db）
  - etl.py — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 計算
  - feature_exploration.py — forward returns, IC, factor_summary, rank
- research/*, ai/* は研究・解析用途のユーティリティ群

---

## 実運用での注意点

- 本リポジトリは「自動売買インフラ」や「判定ロジック」を含みます。実際に発注を行う前に必ず十分な検証を行ってください。
- 本番環境（KABUSYS_ENV=live）では API キー・パスワード管理、ログ出力、監視を厳格に行ってください。
- データのルックアヘッドバイアス対策が組み込まれていますが、バックテスト環境での利用時はデータセット作成手順に注意してください（fetch_listed_info 等は過去のスナップショットを用いること）。

---

もし README に追加したい「実行スクリプト例（cron / systemd）」や「詳細な .env.example」を望む場合は、利用ケース（ローカル実行 / コンテナ / バッチ運用）を教えてください。必要に応じて追記します。