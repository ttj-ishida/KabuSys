# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株のデータ収集・品質管理・リサーチ・AI ニュース解析・市場レジーム判定・監査ログ管理までを含む自動売買基盤のライブラリ群です。DuckDB をデータストアに利用し、J-Quants / RSS / OpenAI（LLM）など外部データソースと連携して、ETL → 品質チェック → ファクター算出 → シグナル生成 → 監査ログ保存までのワークフローを想定しています。

主な特徴
---
- データ ETL（J-Quants からの株価・財務・カレンダー取得、差分取得・バックフィル対応）
- データ品質チェック（欠損、重複、スパイク、日付不整合の検出）
- ニュース収集・前処理（RSS の安全取得、SSRF 対策、トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア化）
- 市場レジーム判定（ETF ma200 とマクロニュース LLM を合成）
- ファクター計算・リサーチユーティリティ（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal / order_request / execution の冪等・トレース可能なスキーマ）
- 環境変数ベースの設定読み込み（.env, .env.local 自動ロード）

必要条件
---
- Python 3.9+（型ヒント / union 演算子等を想定）
- duckdb（Python パッケージ）
- openai Python SDK（OpenAI API を使う機能を利用する場合）
- ネットワークアクセス（J-Quants API、OpenAI、RSS）
- J-Quants / OpenAI / Slack / kabuステーション 等の API 資格情報

環境変数（主要）
---
以下はこのコードベースで参照される環境変数の代表例です（config.Settings を参照）。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で利用）

設定ファイル
- .env / .env.local をプロジェクトルートに置くと自動的に読み込まれます（OS 環境変数優先）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
---
1. リポジトリをクローン / カーソル地点へ移動
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存関係をインストール（例）
   - pip install duckdb openai defusedxml
   - または pyproject.toml / requirements.txt があればそれに従う
4. パッケージを開発モードでインストール（任意）
   - pip install -e .
5. 環境変数を設定
   - プロジェクトルートに .env を作成し、必要なキーを設定（.env.example を参照）
     例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     ```
6. DuckDB 初期化（監査ログ DB など）
   - Python REPL またはスクリプトから init_audit_db を呼び出す（例は下を参照）

基本的な使い方（コード例）
---
- DuckDB 接続を用意して ETL を走らせる（日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースの AI スコアリング（特定日）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
```

- 監査ログ DB 初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- リサーチ関数（ファクター計算例）:

```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

留意点
- OpenAI 呼び出しは各関数で api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定します。API 呼び出しの失敗はフェイルセーフ（多くの場合スコア 0.0 を採用）で設計されていますが、RATE LIMIT 等には注意してください。
- ETL / API クライアントはリトライ・レートリミット制御を実装していますが、実運用ではジョブスケジューラ（cron / Airflow 等）で制御してください。
- DuckDB のバージョン互換性（executemany の空リスト扱いなど）を考慮した実装になっています。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / 設定読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news, calc_news_window 等）
  - regime_detector.py — ETF MA と LLM を組み合わせた市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・raw_news 保存
  - calendar_management.py — 市場カレンダー管理（営業日判定・update job）
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（各チェックと run_all_checks）
  - audit.py — 監査ログ（schema 定義・初期化用）
- research/
  - __init__.py
  - factor_research.py — Momentum/Volatility/Value ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- ai, research, data 以下は更に細分化された機能群を実装

開発・テスト
---
- ユニットテストはモジュールごとに依存注入（モック）で OpenAI / ネットワーク呼び出しを差し替えてテスト可能なよう設計されています。
- 自動環境読み込みはデフォルトで有効ですが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。

貢献・拡張
---
- 新しい ETL ソースや評価指標、取引実行ロジックはモジュールを追加する形で拡張できます。
- 監査ログテーブルは init_audit_schema / init_audit_db を介して冪等に初期化可能です。

最後に
---
この README はコードベースに含まれる主要機能と使い方のサマリです。各モジュールの詳細な挙動・引数・戻り値は該当ソース（src/kabusys/**）の docstring を参照してください。必要があれば導入スクリプトや運用手順、サンプルジョブ（cron/Airflow）も追加できます。