# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注・約定トレース）などの機能を含みます。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（例）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買／データ基盤のためのモジュール群です。  
主に以下の領域をカバーします。

- J-Quants API からの株価・財務・カレンダー取得（rate-limit / retry / id_token リフレッシュ対応）
- DuckDB を用いた ETL（差分更新、バックフィル、品質チェック）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（銘柄別）および市場レジーム判定（ETF + マクロニュース）
- 研究用のファクター計算／特徴量解析ユーティリティ
- 発注・約定までの監査ログスキーマ（冪等性・トレーサビリティ）

設計方針としては「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは再試行・フォールバックを備える」「DuckDB に対する冪等保存」を重視しています。

---

## 主な機能一覧
- データ取得 / 保存
  - J-Quants：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - DuckDB への保存（save_daily_quotes, save_financial_statements, save_market_calendar）
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（統合）
  - ETLResult（実行結果のデータクラス）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック（run_all_checks）
- ニュース処理
  - RSS 取得（fetch_rss）、前処理、raw_news への保存（news_collector）
  - ニュース NLP（score_news）: 銘柄毎のセンチメントを OpenAI で算出して ai_scores に保存
- 市場レジーム判定
  - score_regime: ETF（1321）200日MA乖離とマクロニュースセンチメントを合成して market_regime に保存
- 研究用（Research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン、IC 計算、ファクターサマリー、Zスコア正規化
- 監査ログ（Audit）
  - 監査スキーマ初期化（init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions のテーブル定義とインデックス

---

## セットアップ手順

前提
- Python 3.9+（typing の union 表記/型ヒントを使用しているため推奨）
- DuckDB、openai、defusedxml 等の依存パッケージ

1. リポジトリをクローン／配置
   - .git または pyproject.toml があるディレクトリをプロジェクトルートと見なします（.env 自動読み込みに使用）。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須の値などは後述の「環境変数」参照。

5. DuckDB データベース用ディレクトリを用意（任意）
   - デフォルトでは settings.duckdb_path は `data/kabusys.duckdb`、sqlite 関連は `data/monitoring.db` を指します。必要に応じて変更してください。

---

## 使い方（簡単な例）

以下は基本的な使い方のサンプルコードです。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）を設定してください。

- DuckDB 接続を開いて ETL を実行する例

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')  # ファイルまたは ":memory:"
# target_date を指定しない場合は今日が対象（内部で営業日に調整されます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（特定日）を評価し ai_scores テーブルへ書き込む

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（market_regime への書き込み）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用の DB 初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以降、order/signals/executions を記録するための操作が可能
```

ノート:
- OpenAI の呼び出しを伴う関数（score_news, score_regime）は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を設定して使用してください。
- J-Quants の呼び出しには JQUANTS_REFRESH_TOKEN（Settings で取得）が必要です。get_id_token は内部でこのトークンを用いて id_token を取得します。

---

## 環境変数（Settings による主な設定）
設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` で指定できます（.env.local は上書き）。主なキーは以下の通りです。

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- kabu ステーション
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI / 通知
  - OPENAI_API_KEY (score_news / score_regime で使用)
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベースパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 監視 / 実行プロセス
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- システム設定
  - KABUSYS_ENV: development / paper_trading / live（default: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- 自動 .env 読込制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化

備考:
- settings オブジェクト経由でこれらを参照できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）
以下はコードベースの主要モジュールと概要です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント / OpenAI 呼び出し・検証
    - regime_detector.py  — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の公開インターフェース
    - quality.py          — 品質チェック（欠損/スパイク/重複/日付不整合）
    - news_collector.py   — RSS 収集・前処理・SSRF 対策
    - calendar_management.py — 市場カレンダー管理（営業日判定、calendar_update_job）
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py  — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - research/*（ユーティリティ群）
- そのほか:
  - デフォルトでは data/ 下に duckdb ファイルやワークファイルを置きます（settings で変更可能）。

---

## 注意点 / 運用上のポイント
- ルックアヘッドバイアス回避のため、多くの関数は内部で date.today() を参照せず、明示的な target_date 引数を受け取る設計です。バックテストや再現性のために必ず target_date を明示することが望ましいです。
- OpenAI 呼び出しは外部ネットワーク依存のため、ネットワークエラー時はフォールバック（スコア 0.0）する実装になっていますが、本番運用ではレート制御・コスト管理に注意してください。
- J-Quants API のレート制限（120 req/min）を遵守するため、jquants_client は内部に RateLimiter を持ちます。
- DuckDB に対する executemany の挙動やバージョン依存の注意点（空リスト不可等）がコード内で考慮されています。DuckDB のバージョン互換性には留意してください。

---

## 付録: 連絡先・ライセンス
（ライセンスや貢献ガイドはこのリポジトリに合わせて追記してください）

---

README は以上です。必要であれば、セットアップ用の requirements.txt、サンプル .env.example、または CI / 実行スクリプトのテンプレートを作成します。どれを追加しますか？