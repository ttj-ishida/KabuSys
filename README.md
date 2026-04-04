# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム向けライブラリ群です。  
ETL（J‑Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、ファクター研究、監査ログ（約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J‑Quants API からの差分取得（株価日足・財務・上場銘柄情報・JPX カレンダー）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（run_daily_etl）と結果（ETLResult）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出
- ニュース収集・NLP
  - RSS 収集（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄センチメントスコアリング（score_news）
- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを組み合わせた日次レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリ、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマ初期化・専用 DB 初期化機能
- 設定管理
  - .env（プロジェクトルート）自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 環境に応じたフラグ（development / paper_trading / live）

---

## 依存関係（代表例）

- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- （標準ライブラリ以外は requirements.txt を参照してください）

※ 実行には J‑Quants のリフレッシュトークンや OpenAI API キーが必要です。

---

## 環境変数（主なもの）

KabuSys は環境変数 / .env から設定を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

代表的なキー:

- JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（約定実行を使う場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視設定
- KABUSYS_ENV — environment: development / paper_trading / live
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の形式は一般的な KEY=VAL、export KEY=VAL、シングル/ダブルクォート対応、コメント対応等に対応しています。

---

## セットアップ

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （パッケージ一覧がない場合は duckdb, openai, defusedxml などを個別にインストール）

4. 環境変数設定
   - プロジェクトルートに `.env` として上記キーを設定してください（.env.example を参照する想定）。
   - 自動読み込みはデフォルトで有効（プロジェクトルート検出は .git または pyproject.toml に基づく）。

5. DuckDB 初期化（監査DB を使用する場合）
   - Python から init_audit_db を呼ぶと必要ディレクトリを作成して初期化します（例を後述）。

---

## 使い方（代表例）

以下は Python スクリプトや REPL から呼び出す例です。すべての例は事前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）が設定されていることを前提とします。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（OpenAI 必須）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（1321 MA200 + マクロセンチメント）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB 初期化（監査専用 DB を作る）:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# 以降 conn を使って監査テーブルに書き込みが可能
```

- 市場カレンダー更新ジョブ（J‑Quants から差分取得）:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"保存レコード数: {saved}")
```

- 設定参照（コード内での使用例）:
```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path('data/kabusys.duckdb')
print(settings.is_live)            # 環境が 'live' の場合 True
```

---

## 注意点 / 実行上の留意点

- OpenAI 呼び出しや外部 API 呼び出しはリトライやフェイルセーフを実装していますが、API キーやネットワークエラーにより結果が得られない場合があります。score_news / score_regime は失敗時に部分スキップ・デフォルト値で継続する設計です（例: macro_sentiment = 0.0）。
- ETL は差分取得（最終取得日から）とバックフィルを組み合わせるため、初回は大量データが取得されます。J‑Quants API のレート制限に注意してください。
- news_collector は SSRF 対策や受信サイズ制限、XML パース安全対策（defusedxml）を実装しています。
- DuckDB の executemany に空リストを渡せないバージョンの注意対応が入っています。
- テストしやすさのため、内部の OpenAI 呼び出しや URL オープン関数はパッチ可能（モック化を推奨）な設計です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / .env 読み込み・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントの集約・OpenAI 呼び出し・ai_scores への書込み
  - regime_detector.py — 市場レジーム判定ロジック（ETF 1321 ma200 + マクロ）
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント / 保存ロジック
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — JPX カレンダー管理（is_trading_day / next_trading_day 等）
  - news_collector.py — RSS 収集・前処理・raw_news 保存ロジック
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査スキーマ定義・初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py — モメンタム／バリュー／ボラティリティ等の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ 等

（コードベースのコメントや docstring に各関数の設計方針・副作用が詳細に記載されています）

---

## テスト・開発メモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストから自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部アクセス部分は unittest.mock.patch で差し替え可能に設計されています（例: kabusys.ai.news_nlp._call_openai_api のモック化など）。
- DuckDB を用いたローカルテストでは ":memory:" を利用してインメモリ DB として初期化できます（init_audit_db(":memory:") 等）。

---

この README はコード内の docstring に基づいて要点をまとめたものです。追加の使用例や運用手順（デプロイ、運用監視、定期ジョブ設定など）は運用要件に合わせて別途作成してください。