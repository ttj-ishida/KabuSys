# KabuSys

KabuSys は日本株向けのデータ基盤・研究・自動売買のためのライブラリ群です。J-Quants や RSS、OpenAI（LLM）などを利用し、データ取得（ETL）、データ品質チェック、ニュースセンチメントによるスコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（kabusys.config.settings）
- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - 差分 ETL / バックフィル / 品質チェック（run_daily_etl 他）
  - 市場カレンダー管理、営業日判定ユーティリティ
  - RSS ニュース収集・前処理（SSRF 対策・トラッキング除去）
  - 監査ログ（signal / order_request / execution）テーブル初期化ユーティリティ
- ニュース NLP / AI（kabusys.ai）
  - ニュースを集合的に LLM に送って銘柄ごとのセンチメント（ai_scores）を生成
  - マクロニュースと ETF(1321) 200日MA乖離の合成による「市場レジーム」判定
  - OpenAI 呼び出しはリトライやフォールバック実装あり
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 共通ユーティリティ
  - DuckDB を利用した効率的な SQL ベース処理
  - 外部ライブラリへの依存を最小化（ただし OpenAI SDK, duckdb, defusedxml 等は必要）

---

## 動作環境（推奨）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （必要に応じて）その他標準ライブラリ依存なし

具体的なバージョンや追加パッケージはプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローン／取得：
   - （例）git clone <repo>

2. 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール：
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれを使用）

4. 環境変数の設定：
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
   - 必須の環境変数（主なもの）：
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に使用）
   - 任意／デフォルト設定：
     - KABUSYS_ENV — development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=yourpassword
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=CXXXXXXX
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼ぶ例です。DuckDB 接続は Path を str にして duckdb.connect を使います。

- ETL（日次パイプライン）の実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))  # 省略時は今日
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（ai_scores へ保存）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai import score_news  # kabusys.ai.__init__ は score_news を公開している

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
# または明示的に API キーを渡す:
# score_news(conn, date(2026,3,20), api_key="sk-...")
```

- 市場レジームスコアの判定（market_regime テーブルへの書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を利用
```

- 監査ログデータベースの初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
# conn_audit は duckdb.DuckDBPyConnection
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

---

## 設定と自動 .env 読み込み挙動

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - .env.local は既存の OS 環境変数を上書きできる（テスト時などに有用）
- 自動読み込みを無効化するには環境変数を設定：
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数が未設定の場合、kabusys.config.settings のプロパティ参照時に ValueError が発生します（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（概要）

プロジェクトは src/kabusys 以下に主要モジュールを配置しています。主要なファイルと簡単な説明を示します。

- src/kabusys/
  - __init__.py — パッケージのメタ情報（__version__ など）
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
- src/kabusys/ai/
  - __init__.py — news_nlp の score_news を公開
  - news_nlp.py — ニュースの LLM ベースセンチメントスコアリング（score_news）
  - regime_detector.py — ETF(1321) MA とマクロニュースの LLM スコアを合成して市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント / DuckDB への保存ロジック
  - pipeline.py — 日次 ETL パイプライン run_daily_etl 等
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
  - news_collector.py — RSS フィード収集・正規化・保存
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — Zスコア正規化などの共通統計関数
  - audit.py — 監査ログ（signal / order_request / execution）テーブルの初期化ユーティリティ
- src/kabusys/research/
  - __init__.py — 研究用ユーティリティの公開
  - factor_research.py — モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク関数

（上記以外に strategy / execution / monitoring パッケージが将来的に含まれる想定の __all__ 指定がありますが、今回のコードベースの公開部分は上記が中心です。）

---

## ロギング／実行モード

- 環境変数 KABUSYS_ENV（development / paper_trading / live）で動作モードを制御できます（settings.is_live 等で判定可能）。
- LOG_LEVEL 環境変数でログレベルを制御（DEBUG, INFO, ...）。

---

## テスト・開発のヒント

- OpenAI 呼び出しや外部 API はモジュール内の呼び出し関数（例: _call_openai_api）をモックして単体テストできます（コード内にテスト差し替えを想定した実装が多数あります）。
- 自動 .env 読み込みを無効にしてテスト用の環境を自前で制御するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB はインメモリ（":memory:"）接続をサポートしているため、テストではファイルを作らずに利用できます。

---

## ライセンス・貢献

（ここにプロジェクトのライセンスやコントリビュート手順を追記してください）

---

README は以上です。必要であれば次の項目を追加できます：
- requirements.txt / pyproject.toml に合わせた具体的なインストール手順
- さらに詳しい API リファレンス（各関数の引数・戻り値の一覧）
- データベーススキーマ定義（raw_prices / raw_news / ai_scores / market_regime 等）