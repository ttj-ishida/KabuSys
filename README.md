# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのコアライブラリです。  
ETL（株価・財務・カレンダーの差分取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ／トレーサビリティ、データ品質チェックなどを提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス回避」「DuckDB を用いたローカル永続化」「API 呼び出しに対する堅牢なリトライ・フェイルセーフ」「冪等性」の確保です。

---

## 主な機能

- データ ETL
  - J-Quants API からの株価（日足）、財務データ、JPX カレンダーの差分取得・保存（ページネーション・レート制御・リトライ付き）
  - ETL 結果の品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP
  - RSS 収集、前処理、記事→銘柄紐付け、OpenAI によるセンチメントスコア算出（gpt-4o-mini を想定）
  - 銘柄別の ai_score を ai_scores テーブルへ書込み
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を判定
- 研究用ツール
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ、Z スコア正規化
- 監査ログ（audit）
  - signal → order_request → execution までトレース可能な監査テーブルの初期化・管理（DuckDB）
- カレンダー管理
  - 営業日判定、次/前営業日の取得、カレンダー夜間更新ジョブ
- ユーティリティ
  - 設定管理（.env の自動ロード、環境変数経由）、OpenAI 用の堅牢な呼出しパターン、J-Quants API クライアント、RSS の SSRF 対策など

---

## 必要条件 / 依存パッケージ（代表例）

- Python 3.10+
- duckdb
- openai
- defusedxml
- その他標準ライブラリ

（実プロジェクトでは pyproject.toml / requirements.txt を参照してください。ここでは代表的な pip パッケージ例を示します。）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトが pyproject.toml を持つ場合）pip install -e .
4. 環境変数を設定（.env をプロジェクトルートに置くか OS 環境変数で設定）
   - KabuSys の設定は自動で .env → .env.local をロードします（ただしプロジェクトルートが判定できない場合はスキップ）。
   - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要な環境変数（例）

最低限必要となる鍵・パスの例（.env で設定）:

- JQUANTS_REFRESH_TOKEN=...      # J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD=...         # kabu ステーション API 用パスワード（必須）
- OPENAI_API_KEY=...            # OpenAI API キー（news/regime に必要）
- KABU_API_BASE_URL=...         # optional（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development       # development | paper_trading | live
- LOG_LEVEL=INFO

.env.example を参照して .env を作成してください。

---

## 簡単な使い方（コード例）

以下はライブラリの代表的な呼び出し例です。実運用ではログ設定やエラーハンドリングを適切に行ってください。

- DuckDB 接続の準備（settings からパスを取得）:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを実行）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # None = 本日
print(result.to_dict())
```

- ニュース NLP スコア（指定日分のニュースを処理し ai_scores に書き込む）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY から取得
print(f"書き込み件数: {n_written}")
```

- 市場レジーム算出（ma200 とマクロニュースを合成）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env から
```

- 監査ログ用 DB 初期化:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じて audit_conn をアプリ内で使用
```

- カレンダー判定ユーティリティ:

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI 呼び出しはネットワークやレート制限の影響を受けます。関数はリトライやフェイルセーフを備えていますが、API キーが必須です（api_key 引数で明示的に渡すことも可能）。
- テスト時は内部の _call_openai_api 等をモックして外部 API を呼ばないようにできます（コメントにモック方法の記載あり）。

---

## 実行時のポイント / 動作仕様

- 設定管理: src/kabusys/config.py が .env/.env.local の自動読み込みを行います（プロジェクトルートは .git または pyproject.toml を基準に決定）。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead バイアス対策: 多くの関数（news/régime/research/ETL）は内部で datetime.today() を直接参照せず、target_date を引数として明示する設計です。バックテストでは target_date を適切に指定してください。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われます。
- ニュース収集では SSRF や XML 攻撃対策（URL 検証・defusedxml・ホストのプライベート判定など）を実装しています。
- J-Quants API クライアントはレート制御（120 req/min）とトークンリフレッシュ、リトライを実装しています。

---

## ディレクトリ構成（抜粋）

リポジトリのソースは src/kabusys 以下に配置されています。主なファイル・モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py                # 環境変数 / .env 管理
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py                         # ニュース NLP スコアリング（AI 呼出し、バッチ処理）
  - regime_detector.py                  # 市場レジーム判定（MA200 + マクロセンチメント）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py                   # J-Quants API クライアント（fetch / save）
  - pipeline.py                         # ETL パイプライン（run_daily_etl 等）
  - etl.py (再エクスポート)
  - news_collector.py                   # RSS 収集、前処理、保存
  - calendar_management.py              # 市場カレンダー管理（営業日判定等）
  - quality.py                          # データ品質チェック
  - stats.py                            # zscore_normalize 等
  - audit.py                            # 監査ログテーブル初期化 / init_audit_db
- src/kabusys/research/
  - __init__.py
  - factor_research.py                  # ファクター計算（momentum/value/volatility）
  - feature_exploration.py              # 将来リターン / IC / 統計サマリ

（上記以外にも細かいユーティリティが含まれます。プロジェクト全体のファイル一覧はリポジトリを参照してください。）

---

## テストとモック

- OpenAI など外部 API 呼び出し部分は内部で専用のラッパー関数（例: _call_openai_api）を使用しており、ユニットテスト時はこれらを patch / mock して外部呼出しを防げます。
- HTTP 周り（RSS の _urlopen や J-Quants の _request）も同様にテスト用に差し替え可能です。

---

## ライセンス / 貢献

（ここにプロジェクト固有のライセンス・貢献ルールを明示してください。README にない場合はリポジトリの LICENSE を参照してください。）

---

何か特定の使い方（例: バックテストでのデータ初期化手順、.env.example のテンプレート、CI での ETL 実行方法、あるいは特定モジュールの詳細な API ドキュメント）を README に追記したい場合は、用途に合わせて追記します。必要な内容を教えてください。