# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。  
市場データの蓄積・前処理・特徴量作成、シグナル／発注管理、監査ログ（トレーサビリティ）用のスキーマとユーティリティを提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 要件
- セットアップ手順
- 環境変数（.env）と自動ロード
- 使い方（簡単なコード例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、日本株自動売買システムのための共通基盤ライブラリです。  
DuckDB を用いたデータレイヤ（生データ・整形データ・特徴量・発注関連）と、発注から約定までを完全にトレースする監査ログ（audit）モジュールを提供します。  
設定は環境変数（.env ファイルまたは OS 環境）で行い、アプリケーションやテストから取り込みやすい設計になっています。

---

## 主な機能

- 環境変数／設定管理（.env 自動読み込み、必須チェック）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
- DuckDB スキーマ定義・初期化（冪等処理）
  - Raw / Processed / Feature / Execution 層のテーブル群
  - インデックス定義（頻出クエリ向け）
- 監査ログ（Audit）スキーマ
  - シグナル → 発注要求 → 約定 のトレーサビリティを UUID 連鎖で保持
  - 発注要求は冪等キー（order_request_id）により二重発注を防止
  - 全 TIMESTAMP を UTC 保存（監査初期化時にタイムゾーン設定）
- 各種ユーティリティ（DB 接続取得など）

代表的なテーブル（抜粋）:
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- audit: signal_events, order_requests, executions

---

## 要件

- Python 3.10+
  - コードは |（パイプ）型注釈など Python 3.10 以降の構文を使用
- 依存ライブラリ（最低限）
  - duckdb
- （運用時に必要な外部サービス）
  - J-Quants、kabu API、Slack 等のトークン／接続情報（環境変数で管理）

（実際の環境では Slack SDK や HTTP クライアント、J-Quants クライアント等が別途必要になる想定です）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb
   - その他、運用に必要なパッケージを追加
4. 開発インストール（ローカルパッケージとして使う場合）
   - pip install -e .
     - （プロジェクトに pyproject.toml / setup.cfg / setup.py があれば有効）
5. .env を作成（後述の必須キーを参照）

---

## 環境変数（.env）と自動ロード

- プロジェクトルートは `.git` または `pyproject.toml` を基準に自動判定されます。
- 自動的に読み込まれる順序:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env
- 自動ロードを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の読み込みを行いません（テスト時や CI 等で利用）

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 接続パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン
- SLACK_CHANNEL_ID — Slack 投稿先チャンネルID

オプション／デフォルト:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — 値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の基本的な書き方は typical な KEY=VALUE 形式（シングル／ダブルクォート、コメント、export プレフィックスに対応）です。

---

## 使い方（例）

設定の読み取り:

```python
from kabusys.config import settings

# 必須設定が未設定だと ValueError が発生します
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.is_live)
```

DuckDB スキーマの初期化（アプリ起動時に一度実行）:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して DB を初期化

# 既存 DB に接続する場合（初期化を行わない）
conn2 = get_connection(settings.duckdb_path)
```

監査ログ（audit）スキーマの追加:

```python
from kabusys.data.audit import init_audit_schema

# 既存の DuckDB 接続に監査テーブルを追加する
init_audit_schema(conn)
```

監査専用 DB を別途作る場合:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

パッケージ情報（バージョン）:

```python
import kabusys
print(kabusys.__version__)  # 例: "0.1.0"
```

注意点:
- init_schema / init_audit_db は冪等です。既存のテーブルはスキップされます。
- init_audit_schema はタイムゾーンを UTC に設定します（監査データは UTC 保存が前提）。

---

## ディレクトリ構成

リポジトリ（主要ファイル）の抜粋:

src/
  kabusys/
    __init__.py                # パッケージ定義（__version__ 等）
    config.py                  # 環境変数・設定管理（.env 自動ロード、Settings クラス）
    data/
      __init__.py
      schema.py                # DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
      audit.py                 # 監査ログ（signal_events, order_requests, executions）
      audit.py
      audit.py
      audit.py
      audit.py
      audit.py
    execution/
      __init__.py
    strategy/
      __init__.py
    monitoring/
      __init__.py

（上記は現状の主要モジュールを示します。strategy / execution / monitoring はパッケージの枠組みを提供しています。）

---

## 備考 / 運用メモ

- DB ファイルパスは settings.duckdb_path で管理されます。デフォルトは data/kabusys.duckdb。
- 監査ログは削除しない前提で設計されており、外部キーは ON DELETE RESTRICT を利用しています。運用でデータの扱いには注意してください。
- order_requests テーブルは冪等キー（order_request_id）および複数の CHECK 制約を持ち、limit/stop/market 注文の整合性を DB レイヤで担保します。
- LOG_LEVEL や KABUSYS_ENV による振る舞い切り替えを活用してください（paper_trading 等）。

---

必要であれば、README にテーブル定義の詳細（DDL）や .env.example のサンプル、CI 用の設定、開発フロー（テスト、ローカルでの立ち上げ手順）などを追加します。どの情報を追加したいか教えてください。