# KabuSys

日本株自動売買システムの基盤ライブラリ（KabuSys）。  
環境設定の読み込み、外部APIトークン管理、データベースパスの設定など、戦略・実行・監視モジュールの共通基盤を提供します。

バージョン: 0.1.0

---

## 主な機能

- .env / 環境変数ベースの設定読み込み（自動ロード機能）
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を読み込む
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能
  - OS 既存の環境変数は保護（.env による上書きを防止）
- .env パーサ（以下の形式に対応）
  - `export KEY=value` の形式
  - シングル/ダブルクォート内のエスケープ処理（バックスラッシュを処理）
  - クォート無しの値内のコメント認識（`#` の直前が空白またはタブの場合）
- アプリケーション設定ラッパー（Settings）
  - J-Quants 用リフレッシュトークン（JQUANTS_REFRESH_TOKEN）
  - kabuステーション API 用パスワードおよびベースURL（KABU_API_PASSWORD、KABU_API_BASE_URL）
  - Slack 関連（SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）
  - データベースパス（DUCKDB_PATH、SQLITE_PATH）
  - 環境切替（KABUSYS_ENV: development / paper_trading / live）とログレベル検証
  - 便利プロパティ: is_live / is_paper / is_dev
- パッケージ公開インターフェース: data / strategy / execution / monitoring

---

## セットアップ

以下は一般的な Python 開発環境でのセットアップ手順の例です。

1. レポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに pyproject.toml / requirements.txt があればそこからインストールします。
   - 開発中はパッケージを編集可能モードでインストールすることを推奨します:
   ```
   pip install -e .
   ```
   または
   ```
   pip install -r requirements.txt
   ```

4. .env ファイルを用意
   - 自動的にプロジェクトルートの `.env` / `.env.local` が読み込まれます（必要に応じて環境変数を直接設定しても可）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## .env の例

`.env.example` 相当の参考例:

```
# 必須
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_api_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C0123456789"

# 任意（デフォルトが設定されるもの）
KABU_API_BASE_URL="http://localhost:18080/kabusapi"
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"

# 動作モード: development / paper_trading / live
KABUSYS_ENV=development

# ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
LOG_LEVEL=INFO
```

.env のパースルール（要点）
- 空行や `#` で始まる行は無視
- `export KEY=val` を許容
- クォートあり: エスケープ（`\`）を解釈して閉じクォートまでを値として扱う
- クォートなし: `#` が直前に空白/タブがある場合のみコメントと見なす

---

## 使い方（簡単なサンプル）

設定値は Settings オブジェクト経由で取得します。

```python
from kabusys.config import settings

# 必須トークン（設定されていない場合は例外 ValueError）
jquants_token = settings.jquants_refresh_token

# kabuステーションのベースURL（未設定時はデフォルト）
kabu_base = settings.kabu_api_base_url

# Slack 設定
slack_token = settings.slack_bot_token
slack_channel = settings.slack_channel_id

# データベースパス
db_path = settings.duckdb_path

# 実行環境判定
if settings.is_live:
    print("ライブ運用モードです。")
elif settings.is_paper:
    print("ペーパートレードモードです。")
```

自動ロードを無効化してから明示的に環境変数を読み込みたい場合（テスト等）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## ディレクトリ構成

パッケージは src 配下の `kabusys` モジュールで提供されています。主要ファイル:

- src/kabusys/
  - __init__.py                -- パッケージ初期化（バージョン、公開モジュール）
  - config.py                  -- 環境変数 / 設定管理（自動 .env ロード、Settings）
  - execution/                 -- 注文実行関連モジュール（実装拡張点）
    - __init__.py
  - strategy/                  -- 売買戦略関連（実装拡張点）
    - __init__.py
  - data/                      -- データ取得・保存関連（実装拡張点）
    - __init__.py
  - monitoring/                -- モニタリング / ロギング関連（実装拡張点）
    - __init__.py

プロジェクトルートには通常 `.git` や `pyproject.toml`（ビルド設定）があり、config モジュールはそれらを基準にプロジェクトルートを特定して `.env` / `.env.local` を自動的に読み込みます。

---

## 注意事項 / 補足

- Settings の各プロパティは、必須設定が欠けている場合に ValueError を投げます。実行前に必須環境変数が正しく設定されていることを確認してください。
- 自動ロード時、既に存在する OS 環境変数は保護され、.env による上書きは行われません。ただし `.env.local` は優先度が高く、`override=True` の挙動により OS 変数以外は上書きされます。
- 本リポジトリは「基盤ライブラリ」を意図しており、実際の戦略や注文実行ロジックは各サブパッケージ（strategy / execution / data / monitoring）に実装していく想定です。

---

必要であれば README を拡張して、セットアップの自動化スクリプト、CI の例、テスト実行方法、各サブパッケージの詳細ドキュメントなどを追加します。必要な項目を教えてください。