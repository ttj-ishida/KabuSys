# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants API からのデータ ETL、ニュース収集と LLM ベースのニュースセンチメント解析、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- データ取得（J-Quants）→ DuckDB へ保存する ETL パイプライン。
- RSS ベースのニュース収集と前処理（SSRF/サイズ制限/トラッキング除去など）。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別 / マクロ）。
- 市場レジーム（bull / neutral / bear）の判定（ETF MA と LLM センチメントの合成）。
- 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン、IC 等）。
- データ品質チェック（欠損・重複・スパイク・日付不整合）。
- 監査ログスキーマの初期化と監査用 DB 管理（signal / order_request / executions）。
- 環境変数による設定管理（.env 自動読み込み機構付き）。

---

## 機能一覧

主な機能（モジュール）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、必須設定取得ユーティリティ。
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証リフレッシュ、ページネーション、レート制御、保存関数）。
- kabusys.data.pipeline / etl
  - 差分取得 / 保存 / 品質チェックを統合した日次 ETL（run_daily_etl）。
- kabusys.data.news_collector
  - RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策、トラッキング除去）。
- kabusys.data.quality
  - 欠損・スパイク・重複・日付整合性チェック。
- kabusys.data.calendar_management
  - JPX カレンダー管理、営業日判定・前後営業日取得。
- kabusys.data.audit
  - 監査ログスキーマの作成・初期化（冪等、UTC タイムゾーン固定）。
- kabusys.ai.news_nlp
  - 銘柄ごとのニュースをまとめて LLM に投げ、ai_scores テーブルへ書き込む（score_news）。
- kabusys.ai.regime_detector
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定（score_regime）。
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize 等の研究用関数。

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に `X | None` を使用）
- DuckDB を SQLite 的に使用できる環境
- OpenAI API キー（LLM を使う場合）
- J-Quants のリフレッシュトークン（ETL を使う場合）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install -e .
   - または少なくとも以下をインストール:
     - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある想定で、そこからインストールしてください）

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動でロードされます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須 / 推奨の環境変数例（.env）:
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意)
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development  (valid: development / paper_trading / live)
- LOG_LEVEL=INFO

設定は kabusys.config.settings を通じて参照できます。

---

## 使い方（サンプル）

Python REPL やスクリプト内で呼び出す例を示します。

- DuckDB 接続と ETL 実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア化（AI）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# score_news は OpenAI API キーを環境変数 OPENAI_API_KEY から取得します
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査 DB 初期化（監査用スキーマ）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)
# conn は DuckDB 接続。必要に応じて transactional=True でスキーマ初期化も可能
```

- 研究・因子計算例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

注意点:
- LLM 呼び出しや外部 API 呼び出しはネットワーク/レート制限/課金が発生します。テスト時は対応する呼び出し関数をモックしてください（コード内に patch を想定したコメントがあります）。
- 自動 .env 読み込みはパッケージ初期化時に行われます。テストで環境操作を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主なファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境変数 / .env 管理
    - ai/
      - __init__.py
      - news_nlp.py        -- 銘柄別ニュースセンチメント（score_news）
      - regime_detector.py -- 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（fetch/save）
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - etl.py                 -- ETLResult エイリアス
      - news_collector.py      -- RSS 収集 / 前処理
      - calendar_management.py -- JPX カレンダー管理・営業日ロジック
      - quality.py             -- 品質チェック
      - stats.py               -- zscore_normalize 等
      - audit.py               -- 監査テーブル DDL / 初期化
    - research/
      - __init__.py
      - factor_research.py     -- モメンタム / ボラティリティ / バリュー
      - feature_exploration.py -- 将来リターン / IC / summary / rank
    - monitoring/ (存在する場合: 監視周りのコード)
    - execution/  (存在する場合: 発注/約定関連の実装)
    - strategy/   (存在する場合: 戦略・シグナル生成)

上記は主要モジュールの一覧で、実装内部に多くの補助関数・仕様がコメントで記載されています（例: API リトライ方針、Look-ahead バイアス対策、冪等性の取り扱いなど）。

---

## テスト・デバッグのヒント

- LLM や外部 API 呼び出しはモック可能なように設計されています（内部の `_call_openai_api` / jquants_client の `_request` 等を patch して差し替え）。
- 自動 .env 読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のインメモリ DB を使う:
  - duckdb.connect(":memory:")

---

## 注意事項

- 本ライブラリは売買アルゴリズムの構築支援を目的としています。実際の売買を行う場合は、法規制・委託先証券会社の仕様・リスク管理を十分に確認してください。
- OpenAI や J-Quants への API アクセスはそれぞれの利用規約・料金に従ってください。
- データの「ルックアヘッドバイアス」対策（取得/判定に際して将来情報を使わない設計）を意識してコーディングされていますが、利用側でも運用ルールを守ってください。

---

もし README に加えたい具体的なコマンド例（cron / systemd / Docker / CI の設定）や、.env.example のテンプレート、パッケージ化手順 (pyproject.toml) の記載などがあれば教えてください。必要に応じて追記します。