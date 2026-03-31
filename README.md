# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants）、ニュース収集、AI を用いたニュースセンチメント評価、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株向けのデータ基盤と自動売買パイプラインを構築するための内部ライブラリ群です。主に以下の領域をカバーします。

- データ取得・保存（J-Quants API 経由の株価・財務・カレンダー）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）とニュース→銘柄の紐付け
- LLM（OpenAI）を用いたニュースセンチメントや市場レジームの判定
- リサーチ向けのファクター計算・特徴量解析ユーティリティ
- 監査ログ（シグナル→発注→約定）用のスキーマ初期化ユーティリティ
- 設定管理（.env / 環境変数 / Settings）

設計方針として Look-ahead バイアス回避、冪等性（DB挿入は ON CONFLICT）、フェイルセーフ（API 失敗時に処理継続）を重視しています。

---

## 機能一覧

主なモジュールと機能（抜粋）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準）
  - Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境フラグ）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し（レート制御・リトライ・保存用関数）
  - pipeline: run_daily_etl 等、日次 ETL の実装と ETLResult
  - news_collector: RSS 取得・前処理・SSRF 対策
  - calendar_management: 市場カレンダ管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログスキーマ作成 / init_audit_db
  - stats: zscore_normalize など
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとに LLM でセンチメント評価 → ai_scores へ保存
  - regime_detector.score_regime: MA200 と LLM マクロセンチメントを合成して市場レジーム判定 → market_regime へ保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提:
- Python 3.10 以上（型表記に PEP 604 などを使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（LLM 呼び出し）
- defusedxml（RSS パースの安全化）

推奨手順（Unix 系 / Windows 共通）:

1. 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール（requirements.txt がない場合は手動で）
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 他に linters やテストフレームワークがあれば適宜追加してください。

3. パッケージを開発モードでインストール（リポジトリルートに pyproject.toml / setup.cfg がある前提）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY
   - デフォルト DB パス:
     - DUCKDB_PATH -> data/kabusys.duckdb
     - SQLITE_PATH -> data/monitoring.db

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトでの利用例です。

- Settings（環境変数の利用）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定なら ValueError
```

- DuckDB 接続（デフォルト path を使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は上で作成した DuckDB 接続
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア生成（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- リサーチ関数（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

- 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events/order_requests/executions テーブルが作成される
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES['yahoo_finance'], source='yahoo_finance')
for a in articles:
    print(a['id'], a['datetime'], a['title'])
```

注意:
- LLM（OpenAI）を使う関数は API キー（OPENAI_API_KEY）を期待します。api_key 引数で明示的に渡すことも可能。
- ETL / DB 書き込みはトランザクション管理や冪等性を考慮していますが、本番運用前に小規模で動作検証してください。

---

## 環境変数と設定

主な環境変数（再掲）:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 機能を使う場合必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

settings オブジェクトは kabusys.config.settings から取得できます。

---

## ディレクトリ構成

主要ファイルとモジュールの構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース→銘柄センチメント評価（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 関数）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 収集 / 前処理
    - calendar_management.py — 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize など
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - research/__init__.py
  - その他モジュール（strategy / execution / monitoring 等のプレースホルダは __all__ に含まれています）

（上記は本リポジトリに含まれる主要モジュールの一覧で、各モジュール内に多数の関数・ユーティリティがあります）

---

## テスト・開発

- 自動 .env 読み込みはデフォルトで有効です。ユニットテストや一部環境で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しなど外部依存はモック化可能なように設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB を使った関数は接続を引数で受け取るため、":memory:" 接続でテストできます。

---

以上です。その他、特定機能（例: 発注実装、Slack 通知、戦略本体）の使い方や具体的な運用手順が必要であれば、どの領域を詳しく記載するか教えてください。