# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLP評価、マーケットレジーム判定、監査ログ管理、リサーチ用ファクター計算などを含みます。

## 概要
KabuSys は次の目的を持つモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への冪等保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ニュース収集と銘柄単位での LLM によるセンチメントスコア算出
- マクロセンチメントとETF（1321）MA乖離を組み合わせた市場レジーム判定
- 研究（research）用のファクター計算・統計ユーティリティ
- 監査ログ（signal → order_request → executions）のテーブル初期化ユーティリティ
- 環境変数/設定の一元管理

設計方針として、バックテストでのルックアヘッドバイアス回避（date を明示する）、外部API呼び出しのリトライ・フェイルセーフ、DuckDB を使ったローカル永続化、冪等性を重視しています。

---

## 機能一覧
主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）, Settings オブジェクトで設定取得
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・取得・保存）
  - pipeline: 日次 ETL 実行（run_daily_etl 等）
  - quality: データ品質チェック（check_missing_data、check_spike 等）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - calendar_management: 市場カレンダーの判定・更新ロジック（is_trading_day など）
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出 & ai_scores へ書込
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロセンチメントを合成し market_regime を更新
- kabusys.research
  - factor_research: モメンタム/バリュー/ボラティリティなどのファクター計算
  - feature_exploration: 将来リターン計算・IC・統計サマリなど

---

## セットアップ手順

前提
- Python 3.10+ を推奨（typing | union syntax 等を利用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）可能であること

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml
   - その他プロジェクト依存があれば追加してください（requests 等が必要な箇所は本コードベースでは直接依存していませんが、運用用ユーティリティで必要になる場合があります）

   開発インストール（パッケージ化済みの場合）:
   - pip install -e .

3. 環境変数 / .env を用意
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須（動作に応じて設定）:
     - JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン; 必須 for ETL）
     - OPENAI_API_KEY=（OpenAI APIキー; news_nlp/regime_detector で必要）
     - KABU_API_PASSWORD=（kabuステーション API パスワード、発注系）
   - 任意:
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH, KILL_FLAG_PATH など

   .env の例 (プロジェクトルート/.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な呼び出し例）

※ 以下は Python REPL / スクリプト内での例です。適宜 import と環境設定を行ってください。

基本設定取得
```
from kabusys.config import settings
print(settings.duckdb_path)  # デフォルト data/kabusys.duckdb
```

DuckDB 接続
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

ETL（日次パイプライン）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```
- run_daily_etl は市場カレンダーETL → 株価ETL → 財務ETL → 品質チェック の順で実行します。
- ETLResult により取得・保存件数、品質チェック結果、エラー情報が得られます。

ニュースセンチメント評価（銘柄単位）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"written: {n_written}")
```
- target_date に対して前日 15:00 JST ～ 当日 08:30 JST の記事を対象として ai_scores に書き込みます。
- api_key を None にすると環境変数 OPENAI_API_KEY を参照します。
- 失敗時はフェイルセーフでスキップする設計です。

市場レジーム判定
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```
- ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し market_regime に書き込みます。

監査ログ DB 初期化
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) を呼んで既存の conn にテーブルを作成
```

リサーチ用ファクター計算（例）
```
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

カレンダー・営業日ユーティリティ
```
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026,3,20)
if is_trading_day(conn, d):
    nd = next_trading_day(conn, d)
```

ログ設定（例）
```
import logging
logging.basicConfig(level=settings.log_level)
```

---

## 実運用上の注意
- OpenAI 呼び出しはリトライ・タイムアウト処理を含みますが、API利用量・コストには注意してください。
- J-Quants API はレート制限があるため、jquants_client は内部でスロットリング（120 req/min）を行います。
- .env 自動読み込みはプロジェクトルートの検出に依存します。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- バックテストでのルックアヘッドバイアス防止設計が組み込まれているため、target_date を明示的に渡すことが重要です。
- DuckDB executemany に関する互換性（空リスト渡し不可）などライブラリのバージョン依存に注意してください。

---

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数と Settings
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの NLP スコアリング（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - quality.py               — データ品質チェック
    - news_collector.py        — RSS 取得と前処理
    - calendar_management.py   — マーケットカレンダー操作
    - audit.py                 — 監査ログテーブル定義・初期化
    - etl.py                   — ETL 結果型の再エクスポート
    - stats.py                 — 汎用統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py   — 将来リターン/IC/統計要約など

---

## 参考 / 補足
- 自動環境読み込みは .env/.env.local をプロジェクトルートから読みます（優先順: OS env > .env.local > .env）。
- AI 関連機能は OpenAI API の JSON mode（厳格なJSON出力）を前提とした実装が含まれます。API レスポンスの妥当性チェックを行いますが、モデルの挙動・バージョンによっては想定外の結果が返ることがあります。
- ETL やスキーマ初期化を実行する前に DuckDB のバックアップをとるなどの運用ポリシーを検討してください。

---

もし README に追記したい具体的なコマンド（systemd unit, cron ジョブ、Dockerfile、CI設定 など）やサンプル .env.example を付けたい場合は、その内容を教えてください。必要に応じて実行スクリプトのテンプレートも作成します。