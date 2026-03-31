# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（DuckDB）などを含むモジュール化された実装を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買・リサーチ基盤向けに設計された Python パッケージです。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース収集と LLM によるニュースセンチメント評価（gpt-4o-mini を想定）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用ファクター計算・特徴量解析ユーティリティ
- 発注・約定フローを追跡する監査ログ（DuckDB ベース）
- 環境変数管理と自動 .env ロード機能

設計方針として、ルックアヘッドバイアスを避けること、冪等性・フェイルセーフ性を重視すること、外部 API 呼び出しはリトライやバックオフを備えること、DuckDB を DB 層に用いることが掲げられています。

---

## 主な機能一覧

- data
  - J-Quants クライアント（fetch / save 関数）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS の取得と前処理）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント集約（score_news）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200乖離 + マクロセンチメントを合成）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - .env または環境変数からの設定ロード、Settings オブジェクト（settings）を提供

---

## 動作要件（推奨）

- Python 3.10+
- 必要な主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt / pyproject.toml に従ってください）

---

## 環境変数 / .env

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行プロセス PID ファイルパス（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: one of development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

.env 読み込み順序（優先度低→高）:
- .env （プロジェクトルート）
- .env.local （上書き）
- OS 環境変数は .env より優先

.env のサンプル（例）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンまたはソースを取得
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）
4. 環境変数ファイルを作成（.env / .env.local）
5. 初期 DB を作成する（監査DB など、必要に応じて）

---

## 使い方（クイックスタート）

以下は代表的な利用例です。各処理はモジュール関数をインポートして呼ぶ形です。

- DuckDB 接続の用意:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（run_daily_etl）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（score_news）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は上で用意した DuckDB 接続
# OPENAI_API_KEY は環境変数で設定しておくか、api_key に渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用に別 DB を使う場合）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または :memory:
# audit_conn = init_audit_db(":memory:")
```

- 設定参照例:

```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

---

## 主要 API の説明（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
    - ETL の上位関数。calendar → prices → financials → quality の順で処理。
  - run_prices_etl / run_financials_etl / run_calendar_etl
    - 個別 ETL ジョブ。差分取得と保存を行う。

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を参照し、OpenAI へバッチ送信して ai_scores を更新。

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を更新。

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
    - 各種品質チェックを実行して QualityIssue のリストを返す。

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なファイル / モジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数と Settings
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュース NLP（score_news）
    - regime_detector.py            - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（fetch/save）
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        - 市場カレンダー管理
    - news_collector.py             - RSS 収集
    - quality.py                    - データ品質チェック
    - stats.py                      - 統計ユーティリティ（zscore_normalize）
    - audit.py                      - 監査ログスキーマ初期化
    - etl.py                        - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（momentum/value/volatility）
    - feature_exploration.py        - forward returns / IC / summary / rank
  - monitoring/ (省略: 監視・プロセス監視モジュール想定)
  - execution/  (省略: 発注実装想定)
  - strategy/   (省略: 戦略実装想定)

---

## 注意事項 / 運用上のヒント

- API キー管理:
  - OpenAI / J-Quants のキーは .env や安全なシークレット管理を利用してください。
  - score_news / score_regime は引数で api_key を渡すことも可能です（テスト用）。

- 本番運用:
  - KABUSYS_ENV に `live` を設定すると本番フラグが立ちます。運用時は取り扱いに注意してください。
  - 監査ログ（audit テーブル）は削除しない前提で設計されています。運用でのバックアップ計画を用意してください。

- ルックアヘッドバイアスの回避:
  - モジュールは内部で date.today() や datetime.today() を直接参照しないように設計されていますが、呼び出し側で target_date を明示的に渡して利用することが推奨されます（特にバックテストで重要）。

- ネットワーク／API エラー:
  - J-Quants クライアントや OpenAI 呼び出しはリトライ・バックオフやフェイルセーフを備えています。エラーログを確認し、必要に応じて再実行してください。

---

## 貢献 / 開発

- テスト:
  - 各モジュールの外部呼び出し（HTTP / OpenAI）はモックしやすい設計（例えば _call_openai_api を差し替え）になっています。ユニットテストを書く際はこれらをパッチしてください。

- コーディングスタイル:
  - 型注釈、ログ出力、DuckDB での SQL パラメータバインド（?）の利用を意識してください。

---

本 README は提供されたソースコードの内容に基づいて要約しています。さらに詳しい使い方や API の完全な仕様は各モジュールのドキュメントや docstring を参照してください。必要であれば README の英語版や導入ガイド（サンプルスクリプト、Dockerfile、CI 設定など）も作成します。