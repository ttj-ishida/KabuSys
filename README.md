# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
DuckDB を用いたデータパイプライン、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査（audit）スキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメントスコア算出
- ETF（1321）とマクロ記事を用いた市場レジーム判定（bull/neutral/bear）
- ファクター計算（Momentum / Value / Volatility 等）と研究用統計ユーティリティ
- DuckDB ベースの監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の共通方針として、バックテスト等でルックアヘッドバイアスが入らないよう日付の扱いに注意して実装されています。また、多くの外部 API 呼び出しにはリトライ・レート制御・フェイルセーフが組み込まれています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - market_calendar 管理・営業日判定ユーティリティ
  - news_collector（RSS 取得、前処理、SSRF 対策）
  - 品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - マーケットレジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数と .env ファイル自動読み込み・ validation（Settings オブジェクト）
- monitoring / execution / strategy（パッケージ公開名に含むが、今回のコードベースでの実装は data / ai / research が中心）

---

## 必要要件

- Python 3.10 以上（構文で | 型注釈等を使用）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード）

（プロジェクトに pyproject.toml / requirements.txt があればそちらを参照してインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 代表的なものを手動でインストールする場合:
     - pip install duckdb openai defusedxml
   - プロジェクトを editable インストール（pyproject.toml がある前提）:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml を含むディレクトリ）に `.env` / `.env.local` を置くと、自動でロードされます（config.py の自動ロード機能）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN：Slack 通知を行う場合
   - SLACK_CHANNEL_ID：Slack 通知先チャネル ID
   - KABU_API_PASSWORD：kabuステーション API を使う場合のパスワード
   - OPENAI_API_KEY：OpenAI を利用する場合（ai.score_news / ai.score_regime）
   - （任意）KABUSYS_ENV：development / paper_trading / live（デフォルト development）
   - DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH：監視用 SQLite（デフォルト data/monitoring.db）

   例 `.env`（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=your_password_if_needed
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

6. ディレクトリ（data ファイル保存先）作成
   - DUCKDB_PATH の親ディレクトリ（例 `data/`）が存在しない場合は作成してください。多くの初期化関数は親ディレクトリを自動作成しますが、安全のため用意しておくとよいです。

---

## 使い方（簡単なコード例）

下記は Python REPL やスクリプトからの利用例です。すべて duckdb 接続を渡して動かします。

- DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

# ファイルパスは設定から取得可能
db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア（OpenAI 必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# settings で OPENAI_API_KEY が設定されている前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- マーケットレジーム判定（ETF 1321 の MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- ファクター計算（研究）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は各銘柄ごとの dict のリスト
```

---

## .env 自動読み込みについて

- 起点はこのパッケージの config._find_project_root() で、__file__ を基準に上位ディレクトリを探索し `.git` または `pyproject.toml` を見つけたルート配下の `.env` / `.env.local` を読み込みます。
- 読み込み順序:
  1. OS 環境変数（優先）
  2. .env（override=False: 未設定のもののみセット）
  3. .env.local（override=True: 上書き。ただし既存 OS 環境変数は保護）
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                           — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                        — ニュース NLP スコアリング（score_news）
    - regime_detector.py                 — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント（fetch/save）
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - etl.py                             — ETLResult 再エクスポート
    - calendar_management.py             — 市場カレンダー / 営業日ユーティリティ
    - news_collector.py                  — RSS 取得・前処理・保存
    - quality.py                         — データ品質チェック
    - stats.py                           — zscore_normalize 等
    - audit.py                           — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py                 — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py             — calc_forward_returns / calc_ic / factor_summary / rank
  - ai, research, data のそれぞれに補助ユーティリティが含まれます。

---

## 注意事項 / トラブルシューティング

- OpenAI API
  - OPENAI_API_KEY が必要です。ai モジュールでは API 呼び出しにリトライとフェイルセーフを実装していますが、API レートや料金に注意してください。
- J-Quants API
  - JQUANTS_REFRESH_TOKEN を `JQUANTS_REFRESH_TOKEN` 環境変数に設定してください。get_id_token() により ID トークンを取得します。
  - レート制御（120 req/min）とリトライ処理が組み込まれています。
- DuckDB
  - データ保存時に executemany に空リストを渡すとエラーになる実装があるため、空チェックが入っています。ETL の実行順序や DB スキーマが正しいことを確認してください。
- セキュリティ
  - news_collector は SSRF 対策、gzip サイズ制限、defusedxml を使った安全な XML パースなどを行っています。ただし運用環境ではネットワークポリシー等の追加対策を検討してください。
- 環境検証
  - settings.env / log_level による挙動の切替や、KABUSYS_ENV の値（development / paper_trading / live）に依存する処理があるため、デプロイ時は環境設定を一貫させてください。

---

## 貢献 / ライセンス

本リポジトリに特定の貢献フローやライセンス表記がない場合は、リポジトリ内のドキュメント（CONTRIBUTING.md / LICENSE）を確認してください。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。必要であれば、具体的な CLI、ユニットテストの実行方法、デプロイ手順、監視／アラート設定等についてのドキュメントを追加できます。どの部分を詳しく書いて欲しいか教えてください。