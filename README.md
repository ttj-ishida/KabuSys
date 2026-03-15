# KabuSys

日本株向けの自動売買システム（骨組み）。  
このリポジトリはモジュール構成（データ取得、戦略、注文実行、監視）と設定管理を提供します。現在のバージョンは 0.1.0。

---

## プロジェクト概要

KabuSys は、日本株の自動売買に必要となる基本的なモジュール群（data / strategy / execution / monitoring）と、環境変数・設定を安全に読み込むための設定ユーティリティを含むパッケージです。  
設定ユーティリティはプロジェクトルートの `.env` / `.env.local` を自動的に読み込み、実行環境（development / paper_trading / live）や各種 API トークン、DB パスなどを一元管理します。

パッケージ情報:
- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 機能一覧

- 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）
  - `.git` または `pyproject.toml` を基準にプロジェクトルートを探索するため、CWD に依存しない
  - export プレフィックス、クォート値、コメント等を考慮した .env パーサ
  - 必須環境変数の検査と値取得（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）値の検証
  - 自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- パッケージ骨組み
  - data (データ取得)
  - strategy (売買戦略)
  - execution (注文実行)
  - monitoring (監視・モニタリング)

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の `|` 型ヒント、from __future__ を利用しているため）

基本的なセットアップ例:
1. リポジトリをクローン
   ```bash
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境作成と有効化
   ```bash
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

3. 依存パッケージをインストール  
   プロジェクトが pyproject.toml / requirements.txt を持つ場合はそれに従ってください。開発中はローカルインストールを使うと便利です:
   ```bash
   pip install -e .
   # または requirements.txt がある場合
   pip install -r requirements.txt
   ```

4. 環境変数ファイルを作成  
   プロジェクトルートに `.env`（および必要があれば `.env.local`）を作成します（下記の「.env の例」を参照）。

5. （必要に応じて）自動 env ロードを無効化する場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1   # Unix系
   setx KABUSYS_DISABLE_AUTO_ENV_LOAD 1    # Windows(永続)
   # または PowerShell:
   $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
   ```

---

## .env の例

プロジェクトでは以下の環境変数が利用されます（必須は _require() により強制されます）。`.env` ファイルは次の形式をサポートします: `export KEY=val`, クォート付き値（エスケープ対応）、行末コメント（前にスペース／タブがある場合）など。

```
# J-Quants (必須)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API (必須)
KABU_API_PASSWORD=your_kabu_api_password_here
# 任意: ベースURL（デフォルト: http://localhost:18080/kabusapi）
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (必須)
SLACK_BOT_TOKEN=your_slack_bot_token_here
SLACK_CHANNEL_ID=your_slack_channel_id_here

# データベース（任意: デフォルト値を使用する場合は設定不要）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# システム設定
KABUSYS_ENV=development      # 有効値: development, paper_trading, live
LOG_LEVEL=INFO              # 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

注意:
- OS 環境変数が既に設定されている場合、デフォルトでは `.env` / `.env.local` は上書きしません（.env.local は override=True だが OS 環境変数は保護される）。
- 自動ロードはプロジェクトルートが見つからない場合はスキップされます（プロジェクトルート判定は `.git` または `pyproject.toml` を使用）。

---

## 使い方

設定オブジェクトを経由して必要な設定値にアクセスします。例:

```python
from kabusys.config import settings

# 必須項目の取得（設定されていない場合は ValueError が発生）
jquants_token = settings.jquants_refresh_token
kabu_pass = settings.kabu_api_password

# オプション値（デフォルトがある場合はデフォルトを返す）
kabu_base = settings.kabu_api_base_url

# 環境チェック
if settings.is_live:
    print("本番モードで動作します")
elif settings.is_paper:
    print("ペーパートレーディングモードです")
else:
    print("開発モードです")

# DBパス
duckdb_path = settings.duckdb_path
sqlite_path = settings.sqlite_path
```

将来的には `data`, `strategy`, `execution`, `monitoring` モジュールを拡張し、各モジュールを組み合わせて自動売買フローを構築します。

---

## ディレクトリ構成

主要ファイル/ディレクトリの一覧（現状の最小構成）:

```
.
├─ pyproject.toml (または setup.py)    # プロジェクトルート判定用
├─ .git/                                # 存在する場合プロジェクトルート判定に使用
├─ .env                                  # 環境変数（任意）
├─ .env.local                            # ローカル上書き（任意）
├─ src/
│  └─ kabusys/
│     ├─ __init__.py        # パッケージ定義（__version__ 等）
│     ├─ config.py          # 環境変数・設定管理
│     ├─ data/
│     │  └─ __init__.py     # データ取得関連（拡張予定）
│     ├─ strategy/
│     │  └─ __init__.py     # 売買戦略（拡張予定）
│     ├─ execution/
│     │  └─ __init__.py     # 注文実行（拡張予定）
│     └─ monitoring/
│        └─ __init__.py     # 監視・モニタリング（拡張予定）
└─ README.md
```

---

## 補足・開発者向けメモ

- .env の読み込み順序と優先度:
  1. OS 環境変数（常に最優先、保護される）
  2. `.env.local`（存在する場合、OS にないキーを上書き可能）
  3. `.env`（最低優先。`.env.local` と `.env` の差分管理を想定）

- .env の自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行時など）。

---

README は現状のパッケージ構成に基づいた基本的な説明です。今後、各モジュール（data / strategy / execution / monitoring）を実装・拡張していくことで、具体的なセットアップ手順や運用手順（実際の取引フロー、監視アラート、バックテスト手順など）を追記してください。