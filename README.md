# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants API や RSS を用いたデータ収集、DuckDB を用いた永続化、OpenAI を用いたニュース NLP / 市場レジーム判定、研究用ファクター & 特徴量解析、監査ログ（発注→約定トレーサビリティ）などを提供します。

主な設計方針
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）
- DuckDB への冪等的（idempotent）保存（ON CONFLICT / DELETE→INSERT の方針）
- 外部 API 呼び出しはリトライ・バックオフ・レート制限を実装
- 失敗時はフェイルセーフ（可能なら処理を続行）する設計

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを検出）
  - 必須環境変数チェック（Settings）

- データ ETL / データ品質
  - J-Quants からの株価（daily quotes）、財務データ、マーケットカレンダーの差分取得
  - DuckDB への保存（冪等）
  - 品質チェック（欠損、スパイク、重複、日付不整合）をまとめて実行

- ニュース収集 & NLP
  - RSS フィード収集（SSRF 対策・トラッキング除去・サイズ上限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（ai_scores への永続化）
  - マクロ記事のセンチメント × ETF MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zscore 正規化

- 監査ログ（監査テーブル）
  - signal_events / order_requests / executions の DDL とインデックス定義
  - 監査DB初期化ユーティリティ（UTC タイムゾーン固定）

- J-Quants クライアント
  - レートリミッタ、リトライ、401 の自動トークンリフレッシュ、ページネーション対応
  - DuckDB へ保存するための save_* 関数群

---

## 要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで実装されている部分も多いです）

（実際のプロジェクトでは poetry/requirements.txt を用意してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト配布が pip パッケージになっている場合は pip install -e .）

3. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（および任意で `.env.local`）を置くと自動ロードされます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

.example の最小例（.env）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション（発注に使う場合）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

※ 事前に DuckDB 接続先（settings.duckdb_path のファイル）が設定されていることを想定します。

Python REPL またはスクリプトから呼び出す想定の簡単な例を示します。

1) DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP スコアリング（ai_scores へ書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数でも渡せます
written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written_count}")
```

4) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査DBの初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査テーブルが作成された接続
```

6) リサーチ用ファクター取得例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

# Zスコア正規化（例）
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

7) J-Quants から直接データを取得（テスト / 開発用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
```

---

## 環境変数の主な一覧

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector 使用時）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 開発環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（テスト時に便利）

Settings クラスは必須環境変数が欠けていると ValueError を投げます。

---

## 注意点 / 実運用上のポイント

- OpenAI 呼び出しはリトライ・クリッピングを行いますが、API キー/コストには注意してください。
- ETL は差分取得・バックフィル（デフォルト 3 日）を行います。初回は過去データの取り込みが必要です。
- news_collector では RSS の SSRF や XML 攻撃対策（defusedxml、ホストチェック、サイズ上限）を実装しています。
- audit の DDL は監査トレーサビリティを重視しており、削除を想定していません。バックアップと運用を検討ください。
- DuckDB の executemany に空リストを渡せないバージョン対策など、互換性に配慮した実装が多くあります。

---

## ディレクトリ構成（主要ファイル解説）

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / Settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（ai_scores へ保存）
    - regime_detector.py — ETF MA200 とマクロセンチメント合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ（監査テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research/...（その他解析ユーティリティ）

---

## テスト / 開発時のヒント

- 自動 .env 読み込みはプロジェクトルート検出に基づきます。テスト時は環境変数を直接渡すか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- OpenAI など外部呼び出しを行う関数は内部の _call_openai_api をモックして単体テストしやすい設計です。
- DuckDB はインメモリ(":memory:") でも初期化可能なので単体テストで使えます（audit.init_audit_db など）。

---

## ライセンス / 貢献

（プロジェクトに合わせてここにライセンス表記と貢献ルールを追加してください）

---

この README はコードベースの主要機能・使い方・構成をまとめたものです。必要であれば導入スクリプト、requirements ファイル、デプロイ手順や CI 設定用のドキュメントも追記できます。どの部分を詳しく書くか（例：運用監視、Slack 通知の使い方、kabu ステーション連携のハンドリング等）を教えてください。