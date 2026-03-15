# KabuSys

KabuSys は日本株向けの自動売買システム用パッケージです。モジュールはデータ取得・ストラテジー・注文実行・監視用に分かれており、環境変数（.env ファイル）を用いた設定管理を備えています。

バージョン: 0.1.0

---

## 概要

- 名前: KabuSys
- 目的: J-Quants / kabuステーション 等を利用した日本株自動売買システムの骨組み（設定管理・モジュール構成の提供）
- パッケージ構成: data, strategy, execution, monitoring（各モジュールはパッケージとして用意されています）
- 環境変数を .env ファイルから自動読み込み（プロジェクトルートの検出ロジックあり）

---

## 機能一覧

- 環境変数/.env の読み込み・管理
  - プロジェクトルートを .git / pyproject.toml で検出して .env/.env.local を自動読み込み
  - export KEY=val 形式や引用符つき値（エスケープ対応）、コメント処理に対応
  - OS 環境変数を保護して .env.local で上書きできる仕組み
  - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数
- 設定オブジェクト（settings）経由で必須/任意設定を取得
  - J-Quants / kabu API / Slack / DB 関連などのプロパティを提供
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
- パッケージ名と公開 API: kabusys（__all__ = ["data", "strategy", "execution", "monitoring"]）

※ 実際のデータ取得や発注ロジックは各サブパッケージ（data/strategy/execution/monitoring）に実装する想定です。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージをインストール
   - pyproject.toml / requirements.txt がある場合はそれに従ってください。
   - 開発中であればソースを editable インストールできます:
     ```
     pip install -e .
     ```
   （依存関係は本リポジトリの別ファイルに記載されている想定です）

4. .env ファイルを作成
   - プロジェクトルートに `.env` または `.env.local` を配置します。必要な環境変数は次の「環境変数（必須/任意）」参照。

5. 自動読み込みをテスト
   - デフォルトでパッケージ import 時にプロジェクトルートを検出して .env/.env.local を読み込みます。テストなどで自動読み込みを無効にしたい場合は環境変数を設定してから import してください:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1   # Unix 系
     setx KABUSYS_DISABLE_AUTO_ENV_LOAD 1    # Windows（新しいシェルに反映）
     ```

---

## 環境変数（必須 / 任意）

必須（設定されていないと settings.* プロパティで ValueError を送出）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

システム設定:
- KABUSYS_ENV — 有効値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動読み込みの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとパッケージ import 時の .env 自動ロードを無効化できます。

注意:
- .env の読み込み順は OS 環境 > .env.local > .env（.env.local は既存 OS 変数を保護した上で上書き可）
- .env のパーサは次をサポートします:
  - export KEY=val 形式
  - シングル/ダブルクォートつき値（エスケープに対応）
  - コメント処理（クォート外での # を一定条件下でコメントと判断）

例（プロジェクトルート/.env）:
```
JQUANTS_REFRESH_TOKEN="your_refresh_token_here"
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

- 設定値の取得:
```python
from kabusys.config import settings

# 必須キーは値がなければ ValueError を投げます
refresh_token = settings.jquants_refresh_token
kabu_password = settings.kabu_api_password

# フラグチェック
if settings.is_live:
    print("ライブモードです")
```

- 自動 env 読み込みを無効化してテストする例:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('env:', settings.env)"
```

- パッケージトップレベル:
```python
import kabusys

# サブパッケージは次の名前でアクセス可能
# kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring
```

---

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ初期化、__version__=0.1.0、__all__ にサブパッケージを定義
│     ├─ config.py              # 環境変数・設定管理（.env 読込、Settings クラス）
│     ├─ data/
│     │  └─ __init__.py         # データ取得関連パッケージ
│     ├─ strategy/
│     │  └─ __init__.py         # ストラテジー関連パッケージ
│     ├─ execution/
│     │  └─ __init__.py         # 注文実行関連パッケージ
│     └─ monitoring/
│        └─ __init__.py         # 監視・メトリクス関連パッケージ
└─ (pyproject.toml または setup 等)
```

---

## 開発メモ / 実装上のポイント

- プロジェクトルート検出は config._find_project_root() にて行われ、.git または pyproject.toml を基準に探索します。これにより CWD に依存せずに .env を自動ロードできます。
- .env の自動読み込みは import 時に実行されます。テスト時や特殊用途で不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- settings のプロパティは実行時に環境変数を参照しており、必須項目が未設定の場合は明示的に例外を投げます（早期発見が可能）。

---

必要に応じて README を拡張して、セットアップの詳細（依存ライブラリ、実行コマンド、デプロイ手順、実際のストラテジー実装例など）を追記してください。