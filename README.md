# KabuSys

日本株自動売買プラットフォームのライブラリ群（パッケージ: kabusys）。  
データ取得・ETL、ニュースNLP、AIベースの市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータパイプラインと研究・運用ユーティリティを集めたモジュール群です。主な目的は次のとおりです。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理、ニュースと銘柄の紐付け
- OpenAI を用いたニュースセンチメント解析（銘柄別）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal -> order_request -> execution）のスキーマ定義と初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の方針として、バックテストでのルックアヘッドバイアスを防止するために、内部実装は「外部時刻（date 引数）」に依存する設計を採用しています。また、外部 API 呼び出しはリトライやレート制御、フェイルセーフ（失敗時はスキップや中立値）を備えています。

---

## 主な機能一覧

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch/save の一連処理、認証とリトライ・レート制御
- ニュース収集
  - RSS 取得・前処理・SSRF/サイズ/圧縮対策（kabusys.data.news_collector）
- ニュース NLP（AI）
  - 銘柄別センチメントスコア化: score_news（kabusys.ai.news_nlp）
  - マクロセンチメント + ETF MA 乖離を合成した市場レジーム判定: score_regime（kabusys.ai.regime_detector）
- 研究（Research）
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db（kabusys.data.audit）

---

## 前提・依存関係

- Python >= 3.10（PEP 604 の `X | Y` 型注釈を使用）
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリに加えて urllib / json / time などを利用

インストール例（最低限）:
```
pip install duckdb openai defusedxml
```

パッケージとして開発インストールする場合:
```
pip install -e .
```
（プロジェクトに pyproject.toml / setup.cfg / setup.py が用意されている前提です）

---

## 環境変数 / 設定

kabusys.config.Settings を通して設定を取得します。主な環境変数と説明:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード
- KABU_API_BASE_URL (省略可)  
  kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)  
  Slack 通知に使う Bot Token
- SLACK_CHANNEL_ID (必須)  
  Slack 通知先のチャンネル ID
- DUCKDB_PATH (省略可)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (省略可)  
  SQLite (monitoring) のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (省略可)  
  実行モード（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL (省略可)  
  ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト: INFO
- OPENAI_API_KEY  
  OpenAI API キー（AI 関数呼び出し時の省略可能な引数としても使える）

自動 .env 読み込み:
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env と .env.local を読み込みます。
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - .env.local の値は .env を上書きします（ただし OS 環境変数は保護され上書きされません）
- 自動読み込みを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## セットアップ手順（開発用・最低限）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージのインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（および .env.local）を作成するか、OS 環境変数を設定してください。
   - 必須変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     OPENAI_API_KEY=...
     ```
   - その他:
     ```
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB 等の初期スキーマはプロジェクトの別スクリプトで作成する想定です。監査ログのみ初期化する場合は後述の API を利用してください。

---

## 使い方（代表的な例）

以下はライブラリを直接使う最小の例です。詳細は各モジュールを参照してください。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコア付け（銘柄別）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数で設定するか、api_key 引数で指定可能
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定（マクロ+ETF MA）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "銘柄のモメンタムを計算しました")
```

- 監査ログ（監査DB）を初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.db")
# conn は DuckDB 接続。テーブルが作成されます。
```

各関数の引数や戻り値、動作ポリシー（例: フェイルセーフ、リトライ挙動など）はモジュール内の docstring に詳細が書かれています。

---

## ディレクトリ構成（主要ファイル）

パッケージの主要なディレクトリ／ファイル構成（src/kabusys 以下）:

- __init__.py
  - パッケージの公開 API（data, strategy, execution, monitoring）
- config.py
  - 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — 銘柄別ニュースのセンチメント解析、score_news
  - regime_detector.py — ETF MA とマクロセンチメントの合成で市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - etl.py — ETL インターフェース再エクスポート
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ定義・初期化
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - news_collector.py — RSS 取得・前処理・保存ユーティリティ
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — forward returns, IC, rank, summary
- その他
  - strategy/, execution/, monitoring/ など運用・監視のためのトップレベルモジュール（README での言及対象）

---

## 注意事項 / 運用上の留意点

- OpenAI / J-Quants など外部 API の呼び出しにはコストとレート制限があります。API キーは必ず安全に保管してください。
- AI モジュールは外部 API の失敗を考慮してフェイルセーフ（スコア0.0など）を採用していますが、結果の解釈には注意してください。
- ETL は冪等設計を意識しており、DuckDB への保存は ON CONFLICT による上書き等で重複を排除します。ただし、初期スキーマ作成や運用スクリプトは適切に管理してください。
- テスト時に自動 .env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 参考・拡張

- 各モジュールの docstring（ソースコード）に詳細な設計・挙動が記載されています。実装や挙動を変更する際は docstring の設計原則に沿って行ってください。
- 本 README はコードベースの概要説明です。実運用やデプロイ手順（CI, 実行ユーザー、データベース権限、監視設定等）は別途運用ドキュメントを用意することを推奨します。

---

問題や追加で README に含めたい情報（例: サンプル .env.example、開発用スクリプト、テスト方法など）があれば教えてください。README を補足・拡張して作成します。