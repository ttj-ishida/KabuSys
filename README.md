# KabuSys

KabuSys は日本株向けの自動売買基盤（ライブラリ）です。データ収集・スキーマ管理・戦略・発注・モニタリングを想定したモジュール構成を提供します（現状は設定管理・DuckDB スキーマ初期化などの基盤機能が含まれます）。

バージョン: 0.1.0

主なモジュール:
- kabusys.data — データ/スキーマ関連
- kabusys.strategy — 戦略関連（骨組み）
- kabusys.execution — 発注関連（骨組み）
- kabusys.monitoring — モニタリング関連（骨組み）
- kabusys.config — 環境変数 / 設定管理

---

## 機能一覧

- 環境変数・設定管理
  - プロジェクトルート（.git または pyproject.toml）を基に自動で .env ファイルを読み込み（無効化可能）
  - 必須設定の取得ラッパー（未設定時にエラー）
  - KABUSYS_ENV / LOG_LEVEL の簡易バリデーション
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution の 3〜4 層を想定したテーブル定義
  - インデックス定義、外部キー順を考慮した作成順での初期化関数
  - init_schema(db_path) によりファイルの親ディレクトリ自動作成・テーブル作成（冪等）
  - get_connection(db_path) で既存 DB に接続
- パッケージの骨組み（strategy, execution, monitoring 用の名前空間を準備）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型 | を使用）
- DuckDB を使用するため duckdb パッケージが必要

手順例:

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - pip install duckdb
   - （開発中であれば）プロジェクトを開発モードでインストール
     - pip install -e .

4. 環境変数ファイルを用意
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - 自動ロードは既定で有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - .env の読み込み優先度: OS 環境変数 > .env.local > .env

必要な（想定）環境変数の例:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略時: data/kabusys.duckdb)
- SQLITE_PATH (省略時: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。省略時: development)
- LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL。省略時: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化

.env の書き方（例）:
```
JQUANTS_REFRESH_TOKEN="your_jquants_token"
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

注意: .env のパーサーは以下に対応しています
- export KEY=val 形式
- シングル/ダブルクォート内のエスケープ処理（バックスラッシュ）
- クォート無しの場合は "#" の前にスペースがあるとコメントとみなす

---

## 使い方（簡単な例）

- 設定の取得:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url  # デフォルト: http://localhost:18080/kabusapi
print(settings.env, settings.log_level)
```

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)

# 以降 conn.execute("SELECT ...") でクエリ実行可能
```

- 既存 DB へ接続（スキーマ初期化を行いたくない場合）:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みを無効化したい場合（テストなど）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 設計上のポイント / 補足

- 設定の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。CWD に依存しないためパッケージ配布後も期待通り動作します。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- init_schema は冪等（既存テーブルはスキップ）かつ db_path の親ディレクトリを自動作成します。":memory:" を指定するとインメモリ DB を使用します。
- KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の値は検証され、無効な値を設定すると ValueError が発生します。
- .env のロード順と上書きルール:
  - OS 環境変数は上書きされません（保護されます）。
  - .env を読み込み（override=False）で未設定のキーのみセット。
  - .env.local を読み込み（override=True）で .env の値を上書き（ただし OS 環境変数は保護）。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py                # パッケージ初期化（__version__ = "0.1.0"）
    - config.py                  # 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・init_schema / get_connection
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

その他:
- .env, .env.local（プロジェクトルート、必要に応じて作成）
- data/（デフォルトの DB ファイル格納先）

---

## 今後の拡張案（参考）
- J-Quants / kabu API クライアント統合
- 戦略のプラグイン機構（strategy 実装とバックテスト）
- 注文実行フロー（signal -> order -> trades）とリアルタイム監視
- モニタリング用 DB（SQLite）連携 & Slack 通知

---

問い合わせや貢献は README のあるリポジトリに Issue / PR でお願いします。