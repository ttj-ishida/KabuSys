# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォーム向けライブラリ群です。ETL による市場データ収集、ニュースの NLP による銘柄センチメント算出、ファクター計算・リサーチユーティリティ、監査ログ（オーディット）やマーケットカレンダー管理など、取引システムと研究環境の共通基盤を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部処理で現在時刻を直接参照しない等）
- DuckDB を中心としたローカルデータストア
- J-Quants / OpenAI 等の外部 API を組み合わせた堅牢なリトライ・フォールバック処理
- 冪等性と監査トレーサビリティ重視

---

## 機能一覧

- 環境設定読み込み（.env 自動読み込み、必須環境変数の検査）
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）から .env / .env.local を読みます。無効化可（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- データ ETL（J-Quants クライアント）
  - 日次株価（日足 OHLCV）取得・保存（ページネーション対応、レート制御、リトライ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分取得 / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策、URL 正規化、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア算出（ai_scores へ書き込み）
  - マクロニュースのセンチメントと ETF の MA200 乖離を合成した市場レジーム判定
  - API 呼び出しはリトライ / フェイルセーフ設計
- 研究用ユーティリティ（ファクター計算・特徴量探索）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブルと初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止
- ユーティリティ
  - 汎用統計関数、カレンダー管理、ETL 結果データクラス等

---

## 必要な環境変数

主に次の環境変数が使用されます（必須は明記）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB のデータファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必要）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト INFO）

.env ファイル例（プロジェクトルートに作成）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードを無効にする場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## セットアップ手順

1. リポジトリをクローン
   - ソースが src/ 配下に配置されている想定です。

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須と思われるパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を参照してインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに .env を作成（上記例参照）。
   - または環境に直接設定。

5. データベース用ディレクトリの作成（必要であれば）
   - mkdir -p data

6. 監査ログ用 DB 初期化（任意）
   - 下記の Usage セクション参照。

---

## 使い方（例）

以下は代表的な利用例です。全て Python スクリプト / REPL から実行できます。

- 共通準備:
  - settings をインポートして設定を参照
  - DuckDB 接続は duckdb.connect(settings.duckdb_path) で取得

例: 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

例: ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境から利用
print(f"scored {count} codes")
```

例: 市場レジーム判定（MA200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("score_regime done", res)
```

例: 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または ":memory:" を指定
# audit_conn: DuckDB 接続、監査テーブルが作成される
```

例: J-Quants の ID トークン取得（ライブラリ内部でも利用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
print(token[:8], "...")
```

注意:
- AI 周りの関数は OpenAI API キー（OPENAI_API_KEY）を必要とします。
- ETL や API 呼び出しはネットワーク/レート制限を受けます。適切な ID トークンと API 制限の理解が必要です。
- データ書き込みは DuckDB に対して冪等的に行われますが、バックアップの運用を推奨します。

---

## ディレクトリ構成

リポジトリ（src/kabusys）内のおおまかな構成:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数・設定管理（.env 自動読み込み等）
    - ai/
      - __init__.py
      - news_nlp.py             — ニュースの NLP（OpenAI 呼び出し、ai_scores 書込）
      - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
    - data/
      - __init__.py
      - calendar_management.py  — 市場カレンダー管理（営業日判定、更新ジョブ）
      - etl.py                  — ETL の公開インターフェース（ETLResult 再エクスポート）
      - pipeline.py             — 日次 ETL パイプライン（prices, financials, calendar）
      - stats.py                — 汎用統計ユーティリティ（zscore_normalize 等）
      - quality.py              — データ品質チェック
      - audit.py                — 監査ログ（DDL、初期化ユーティリティ）
      - jquants_client.py       — J-Quants API クライアント（取得 / 保存 / レート制御）
      - news_collector.py       — RSS ニュース収集・前処理（SSRF 対策等）
    - research/
      - __init__.py
      - factor_research.py      — Momentum / Value / Volatility 等のファクター計算
      - feature_exploration.py  — 将来リターン、IC、統計サマリー等
    - (strategy/, execution/, monitoring/) — パッケージ初期化で公開予定（実装が別途存在する想定）

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に受け取る設計で、外部サイドエフェクト（本番口座の発注等）は研究用関数では行わないよう分離されています。

---

## 注意事項 / ベストプラクティス

- Look-ahead Bias に注意：
  - ライブラリ内部では静的に target_date を受け取り、datetime.now()/date.today() 等を直接使わないよう配慮されていますが、ユーザ側で運用時に誤って未来データを参照しないようにしてください。
- API キー／トークンの管理：
  - J-Quants トークンや OpenAI キーは .env / 環境変数で安全に管理してください。コードや公開リポジトリに埋め込まないでください。
- レート制限：
  - J-Quants クライアントは固定間隔スロットリングで 120 req/min を守る設計ですが、追加の API 呼び出しを行う際は注意してください。
- DuckDB の互換性：
  - 一部実装は DuckDB バージョン特性（executemany の挙動等）を考慮しています。DuckDB のバージョンに依存する挙動があるため、安定バージョンを使用してください。

---

この README はコードベースの主要機能と使い方をまとめたものです。実運用や開発時には pyproject.toml / requirements.txt / CONTRIBUTING.md 等のプロジェクトルートのドキュメントも参照してください。質問や追加の利用例が必要な場合は教えてください。