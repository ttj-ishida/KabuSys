# KabuSys

日本株自動売買システム用の軽量ライブラリ（パッケージ骨格）。  
このリポジトリは設定管理、データ・戦略・実行・モニタリング用のパッケージ構成を提供します。現時点ではコアは設定読み込みや環境管理に重点が置かれています。

## 主な特徴
- .env ファイルと環境変数からの設定自動読み込み（プロジェクトルート自動検出）
- 複数環境対応（development / paper_trading / live）
- ログレベル検証（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- J-Quants / kabuステーション / Slack / データベース用の設定プロパティを提供する Settings クラス
- パッケージとしてのモジュール分割（data / strategy / execution / monitoring）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントや Path | None の構文を使用しているため）
- 仮想環境の利用を推奨

1. リポジトリをクローンして作業ディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成と有効化（例: venv）
   ```
   python -m venv .venv
   # Unix/macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

3. 開発インストール（パッケージを編集可能モードでインストール）
   ```
   pip install -e .
   ```
   ※requirements.txt / pyproject.toml がある場合は適宜依存関係をインストールしてください。

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - 自動読み込みはデフォルトで有効です。テストなどで自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）

必須（使用する機能に応じて）
- JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API 接続パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルトあり
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリングDB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL。デフォルト: INFO）

注意:
- Settings のプロパティ（必須とされるもの）は未設定の場合 ValueError を送出します。
- KABUSYS_ENV と LOG_LEVEL は許容値で検証されます。

---

## .env 読み込みの挙動

- 自動読み込みの優先順位: OS環境変数 > .env.local > .env
- プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（これにより実行カレントディレクトリに依存しません）。
- `.env` のパース挙動:
  - `export KEY=val` 形式に対応
  - シングル／ダブルクォートをサポートし、クォート内のバックスラッシュエスケープを処理
  - クォートされていない値のコメント認識は、`#` の直前が空白またはタブの場合に限る
- OS 環境変数はプロテクトされ、`.env` / `.env.local` で上書きされません（ただし `.env.local` は `.env` より優先して読み込み、既存の OS 環境変数以外は上書き可能）。

自動ロード無効化:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# Windows PowerShell:
$env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"
```

---

## 使い方（簡単な例）

- パッケージのバージョン確認:
```python
from kabusys import __version__
print(__version__)  # 例: "0.1.0"
```

- 設定値の取得:
```python
from kabusys.config import settings

# 必須項目は未設定だと ValueError を送出します
token = settings.jquants_refresh_token
kabu_pwd = settings.kabu_api_password

# オプション項目・パス
print(settings.kabu_api_base_url)
print(settings.duckdb_path)   # Path オブジェクト
print(settings.sqlite_path)   # Path オブジェクト

# 環境判定ユーティリティ
if settings.is_live:
    print("本番環境 (live)")
elif settings.is_paper:
    print("ペーパートレード環境")
else:
    print("開発環境")
```

- 例外処理の例:
```python
from kabusys.config import settings

try:
    token = settings.jquants_refresh_token
except ValueError as e:
    # .env を作成するか環境変数を設定してください
    print("設定エラー:", e)
```

- Slack や kabu API を使うモジュールを実装する際は、settings のプロパティを利用して安全に設定値を取得してください。

---

## .env 例（サンプル）
以下は .env に書く例です（実際のトークン・パスワードは適切に置き換えてください）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# kabuステーション
KABU_API_PASSWORD='your_kabu_api_password'
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_channel_id

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: 値に空白や特殊文字がある場合はクォートしてください。クォート内ではバックスラッシュでエスケープできます。

---

## ディレクトリ構成

以下は現状の主要なファイル／ディレクトリ構成です:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージ公開用（__version__, __all__）
│     ├─ config.py            # 環境変数・設定管理（自動 .env 読み込み、Settings）
│     ├─ data/
│     │  └─ __init__.py       # データ関連モジュール（未実装のプレースホルダ）
│     ├─ strategy/
│     │  └─ __init__.py       # 売買戦略関連モジュール（未実装のプレースホルダ）
│     ├─ execution/
│     │  └─ __init__.py       # 注文実行関連モジュール（未実装のプレースホルダ）
│     └─ monitoring/
│        └─ __init__.py       # モニタリング関連モジュール（未実装のプレースホルダ）
└─ README.md
```

各サブパッケージ（data / strategy / execution / monitoring）は拡張ポイントです。プロジェクト要件に応じて機能を実装してください。

---

## 開発メモ / 実装上の注意点
- settings のプロパティは実行時に環境変数を読み取ります。単体テスト等で環境を固定したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を有効にして自前で環境設定を行ってください。
- .env の自動検出は、パッケージ配布後でも動作するようにファイル自体の位置（__file__ を基点）を探索しています。作業ディレクトリに依存しない点に留意してください。
- 将来的に各サブパッケージに具体的な実装（戦略の登録・バックテスト、注文実行ラッパー、データ取得クライアント、モニタリング保存処理など）を追加してください。

---

必要であれば README に追加する内容（API使用例、CI/CD 設定、デプロイ手順、テスト実行方法等）をお知らせください。