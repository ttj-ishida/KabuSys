# KabuSys

日本株向けの自動売買システムのコアライブラリ（プロトタイプ）。  
モジュール化された設計で、データ取得・スキーマ管理、特徴量生成、戦略、発注/約定管理、監視などを統合するための共通基盤を提供します。

主な目的は、J-Quants や kabuステーション等の外部サービスと連携しつつ、DuckDB を用いたローカルデータ管理と戦略/発注ワークフローを容易にすることです。

## 主な機能
- 環境変数ベースの設定管理（自動でプロジェクトルートの .env / .env.local を読み込み）
- DuckDB を用いた冪等なスキーマ初期化（Raw / Processed / Feature / Execution の多層スキーマ）
- 各レイヤーに対応したテーブル定義（価格、財務、ニュース、特徴量、シグナル、注文、約定、ポジション等）
- モジュール構造（data, strategy, execution, monitoring）による責務分離
- Slack / kabu API / J-Quants 等の外部連携のための設定プレースホルダ

## 必要条件
- Python 3.10+
- DuckDB（Python パッケージ `duckdb`）
- （用途に応じて）kabuステーションクライアント、Slack SDK、J-Quants クライアント等

例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb
```

将来的にパッケージ化されている場合は `pip install -e .` 等でインストールしてください。

## セットアップ手順

1. リポジトリをクローン/取得
2. Python 環境を準備（推奨: venv）
3. 依存パッケージをインストール
   - 必須: duckdb
   - 任意: Slack / J-Quants / kabu API クライアント（実装に依存）
4. プロジェクトルートに `.env`（必要な環境変数）を作成
   - 自動読み込みについて:
     - パッケージ起点で .env と .env.local をプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から読み込みます
     - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
5. スキーマ初期化（DuckDB）
   - サンプル:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - メモリ DB を使う場合:
     ```python
     conn = init_schema(":memory:")
     ```

### 必要・推奨の環境変数
（プロジェクトで参照されている値の一覧）

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD
  - kabuステーション API のパスワード
- SLACK_BOT_TOKEN
  - Slack ボットトークン
- SLACK_CHANNEL_ID
  - 通知先 Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV (default: "development")
  - 有効値: development, paper_trading, live
- LOG_LEVEL (default: "INFO")
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABU_API_BASE_URL (default: "http://localhost:18080/kabusapi")
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 値が設定されていると .env 自動ロードを無効化

.env のパースは POSIX ライクな記法（export プレフィックスやクォート、インラインコメント等）に対応しています。`.env.example` を参考にしてください（リポジトリに例が無い場合は上の必須キーを配置してください）。

## 使い方（簡単なサンプル）

- 設定の利用
```python
from kabusys.config import settings

print(settings.duckdb_path)     # DuckDB ファイルパス (Path)
print(settings.is_live)         # 本番判定
```

- スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 初回は init_schema() を呼んでテーブルを作成
conn = init_schema(settings.duckdb_path)

# 既存 DB へ接続するだけなら get_connection()
conn2 = get_connection(settings.duckdb_path)

# DuckDB のクエリを実行
with conn:
    conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

- 自動環境読み込みを無効にしてテストする
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('loaded', settings.duckdb_path)"
```

## ディレクトリ構成

現在の主要ファイル / ディレクトリは以下のとおりです。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義と初期化関数（init_schema, get_connection）
    - strategy/
      - __init__.py            # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py            # 発注 / 約定 管理（拡張ポイント）
    - monitoring/
      - __init__.py            # モニタリング関連（拡張ポイント）

README 等と同じ階層に pyproject.toml や .git があると自動的にプロジェクトルートとして判定され、.env 自動読み込みが行われます。

## 実装上のポイント / 注意事項
- config.py はプロジェクトルートから `.env` / `.env.local` を自動読み込みします。OS 環境変数を保護する挙動（.env.local の override 機能）を持ちます。
- settings のプロパティは未設定の必須キーを参照すると ValueError を投げます。テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか、適切に環境変数を設定してください。
- schema.py の init_schema は冪等（既存テーブルがあれば作成をスキップ）です。初回実行時に親ディレクトリを自動作成します。
- DuckDB の SQL DDL には外部キーやチェック制約、インデックスが含まれており、実運用を見据えたスキーマ設計になっています。

## 今後の拡張案
- strategy パッケージに具体的なアルゴリズム実装（バッチ/リアルタイム）
- execution パッケージに kabu API ラッパーと発注ロジック
- monitoring パッケージに Slack 通知・ダッシュボード連携
- テスト用のフィクスチャ、CI 用の DB 初期化スクリプト

---

問題や実装に関する質問、ドキュメント追加の要望があれば教えてください。README に含めたい追加の使用例や環境変数の説明があれば追記します。