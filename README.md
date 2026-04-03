# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（ライブラリ群）です。  
ETL（J-Quants 連携）、ニュース収集・LLM を用いたニュース NLP、ファクター研究、監査ログ（オーダー/約定トレース）などの機能を組み合わせて、研究→シグナル生成→発注までのワークフローを支援します。

バージョン: 0.1.0

---

## 概要 (Project overview)

KabuSys は以下の領域をカバーする Python モジュール群です。

- データ収集・ETL: J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存するパイプライン。
- データ品質: 欠損・スパイク・重複・日付不整合などの品質チェック。
- ニュース収集: RSS からニュースを収集して raw_news テーブルへ冪等保存（SSRF 対策／前処理実装）。
- ニュース NLP / LLM スコアリング: OpenAI を用いて銘柄別センチメントやマクロセンチメントを評価（JSON Mode を利用）。
- 研究・ファクター: Momentum / Value / Volatility 等のファクター算出や将来リターン・IC 計算、Z スコア正規化等。
- 監査ログ: 戦略→シグナル→発注→約定の監査テーブルを作成するユーティリティ（DuckDB ベース）。
- 設定管理: .env の自動ロード、環境変数からの設定取得。

設計方針の特徴:
- ルックアヘッドバイアスを避ける（target_date を明示・内部で date.today() を参照しない関数設計など）。
- 冪等操作（DB への保存は ON CONFLICT / DO UPDATE 等で上書き）を優先。
- 外部 API 呼び出しはリトライ・バックオフやフェイルセーフを備える。

---

## 主な機能一覧 (Features)

- ETL（差分取得、バックフィル、品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- J-Quants クライアント（fetch / save 系）
  - 認証トークン自動リフレッシュ、レートリミット遵守、ページネーション対応（kabusys.data.jquants_client）
- ニュース収集（RSS）と前処理（SSRF 対策、URL 正規化、トラッキング除去）
  - fetch_rss / preprocess_text（kabusys.data.news_collector）
- ニュース NLP（OpenAI を用いた銘柄別スコアリング）
  - score_news（kabusys.ai.news_nlp）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）
  - score_regime（kabusys.ai.regime_detector）
- ファクター計算・研究ツール
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary（kabusys.research）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- 監査ログ（監査テーブルの初期化・専用 DB の作成）
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 設定管理
  - Settings クラス（kabusys.config.settings）：J-Quants トークン、kabu API 関連、DB パス等を環境変数から取得

---

## セットアップ手順 (Setup)

前提
- Python 3.10+（PEP 604 の | 型などを利用）
- システムに必要な外部ライブラリ：duckdb, openai, defusedxml など

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt や pyproject.toml がある場合はそれに従ってください。

4. 環境変数設定 (.env)
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   主要な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  （必須：J-Quants 認証）
   - OPENAI_API_KEY=<your_openai_api_key>               （score_news / score_regime を使う場合）
   - KABU_API_PASSWORD=<password>                       （kabu API を使う場合）
   - KABUSYS_ENV=development|paper_trading|live         （環境切替）
   - LOG_LEVEL=INFO|DEBUG|...                           （ログレベル）
   - DUCKDB_PATH=data/kabusys.duckdb                    （デフォルトの DuckDB ファイルパス）
   - SQLITE_PATH=data/monitoring.db                     （監視 DB 等）

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方 (Usage examples)

以下は基本的な Python からの呼び出し例です。各関数は DuckDB 接続を受け取ることが多い点に注意してください。

1) 設定の読み取り
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) DuckDB 接続を使った日次 ETL（データ収集）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP（OpenAI を使って銘柄別スコアを作成）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
# OPENAI_API_KEY が環境にない場合は api_key="sk-..." を引数で渡せます
```

4) 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path と別に監査用 DB を作ることも可能
audit_conn = init_audit_db(settings.duckdb_path)
# またはインメモリ:
# audit_conn = init_audit_db(":memory:")
```

6) 研究（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

注意点:
- LLM（OpenAI）を用いる関数は API キーを環境変数 OPENAI_API_KEY から取得します。引数で直接渡すことも可能です。
- ETL/API 通信部分はネットワークや外部 API に依存するため、適切なトークンとネットワーク環境が必要です。
- 関数群はルックアヘッドバイアス防止設計になっているため、target_date を明示的に与えることが推奨されます。

---

## 設定 (Environment / .env の扱い)

- 自動ロード順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数（再掲）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - OPENAI_API_KEY（LLM 使用時）
  - KABU_API_PASSWORD, KABU_API_BASE_URL（kabu ステーション連携）
  - DUCKDB_PATH, SQLITE_PATH（DB ファイルパス）
  - PID_FILE_PATH, KILL_FLAG_PATH（監視関連）
  - KABUSYS_ENV（development/paper_trading/live）
  - LOG_LEVEL（ログレベル）

設定は kabusys.config.settings 経由でアクセスできます（例: settings.jquants_refresh_token, settings.duckdb_path）。

---

## ディレクトリ構成 (Directory structure)

主要なファイルとモジュールは以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の再エクスポート
    - news_collector.py              — RSS 収集・前処理
    - calendar_management.py         — マーケットカレンダー管理
    - quality.py                     — 品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査テーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - research/ などに関連する補助モジュール
  - その他（strategy / execution / monitoring 等のプレースホルダ）

（実際のリポジトリではさらに細かなモジュールや補助コードが存在する可能性があります）

---

## トラブルシューティング

- ValueError: 環境変数が未設定
  - settings のプロパティは必須のキーがないと ValueError を発生させます（例: JQUANTS_REFRESH_TOKEN）。
  - .env を作成して必要なキーを設定してください。

- OpenAI / J-Quants の API エラー
  - ネットワーク・API制限・認証エラー等が発生します。ログを確認し、API キーやトークンの有効性、レート制限を確認してください。
  - モジュール内はリトライ・バックオフを実装していますが、キーの無効や quota 超過はユーザー側で対処が必要です。

- DuckDB スキーマ
  - ETLや audit 初期化前に所定のテーブルが存在しないと関数の一部は None を返したり、空結果になります。必要に応じて init_audit_db を実行して監査テーブルを作成してください。

---

必要に応じて README に示す各例を実行するための追加コマンド（テストスクリプトや CLI）をプロジェクトに追加できます。実運用にあたってはログ設定・プロセス監視（pid file / kill flag）・監視アラート（LINE 等）を組み合わせて運用してください。