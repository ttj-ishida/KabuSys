# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（開発初期段階）

このリポジトリは、データ収集・永続化、戦略層、発注管理、監査ログ、モニタリングなどを想定した基盤ライブラリ群を提供します。まずはデータ取得（J-Quants）や DuckDB スキーマの初期化周りが実装されています。

## 主要な特徴
- 環境変数ベースの設定管理（.env / .env.local を自動読み込み、必要に応じて無効化可）
- J-Quants API クライアント
  - 日足（OHLCV）、財務諸表（四半期）、JPX マーケットカレンダー取得機能
  - レート制限（120 req/min）を厳守するスロットリング
  - リトライ（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制
  - ページネーション対応
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル群を定義
  - インデックスや制約を含む冪等な初期化関数
- 監査ログ（audit）モジュール
  - シグナル→発注→約定までトレース可能な監査テーブル
  - 冪等キー、タイムスタンプ（UTC）、ステータス管理を考慮
- (骨子) strategy / execution / monitoring 用のパッケージ構成を用意

## 必要条件
- Python 3.10 以上（型ヒントに union 演算子および from __future__ の注釈を想定）
- duckdb（DuckDB Python パッケージ）
- ネットワークアクセス（J-Quants API へアクセスする場合）
- （任意）kabuステーション API の使用環境、Slack Bot トークン等

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb"
# パッケージを編集可能インストールする場合（プロジェクトルートで）
pip install -e .
```

（requirements.txt／pyproject.toml はこのサンプルに含まれていません。実際のプロジェクトでは依存管理ファイルを追加してください。）

## 環境変数（主なキー）
Settings クラス経由で以下の環境変数を参照します。必須のものは README 内で明記します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID（必須）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

自動 .env ロード:
- プロジェクトルート（.git もしくは pyproject.toml がある場所）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

.env のパースはシェル形式のエクスポート記法（export KEY=val）やシングル／ダブルクォート、インラインコメントなどをある程度サポートします。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（ローカルでの基本）
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```
2. Python 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージのインストール
   ```bash
   pip install duckdb
   # 必要なら他の依存をインストール
   ```
4. .env を作成して必要な環境変数を設定
5. DuckDB スキーマ初期化（サンプルコード参照）

## 使い方（簡単なコード例）
以下は J-Quants から日足を取得して DuckDB に保存する最小例です。

```python
from kabusys.data import jquants_client, schema
from kabusys.config import settings

# DB 初期化（ファイルは settings.duckdb_path を使用）
conn = schema.init_schema(settings.duckdb_path)

# J-Quants から日足を取得（全銘柄、期間指定可）
records = jquants_client.fetch_daily_quotes(date_from=None, date_to=None)

# DuckDB に保存（raw_prices テーブルに ON CONFLICT DO UPDATE で保存）
n = jquants_client.save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

トークンを直接取得する例（必要に応じて）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用して ID トークンを取得
```

監査ログを既存接続に追加する例:
```python
from kabusys.data import audit
# schema.init_schema() で得た conn を渡す
audit.init_audit_schema(conn)
```

テストや CI で自動読み込みを止めたいとき:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# あるいは Python 実行前に環境変数を設定
```

ログレベルや環境判定は settings オブジェクトを通して利用できます:
```python
from kabusys.config import settings
if settings.is_live:
    # 本番固有の処理
    pass
```

## ディレクトリ構成
プロジェクトは src 配下にパッケージ形式で配置されています。主なファイルとモジュールは以下のとおりです。

- src/kabusys/
  - __init__.py                — パッケージ定義（version 等）
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - schema.py                — DuckDB スキーマ定義・初期化
    - audit.py                 — 監査ログ（signal → order → execution のトレース用）
  - strategy/
    - __init__.py              — 戦略層（骨子）
  - execution/
    - __init__.py              — 発注 / 実行層（骨子）
  - monitoring/
    - __init__.py              — モニタリング（骨子）

（上記はこのコードベースに含まれるファイル一覧に基づく抜粋です。）

## 注意点 / 補足
- J-Quants API 利用時はレート制限や利用規約に従ってください。本クライアントは 120 req/min を前提にスロットリング制御を実装しています。
- DuckDB のテーブル定義では制約（チェック・外部キー）やインデックスを設定しています。スキーマ初期化は冪等です（既存テーブルがあっても上書きしません）。
- 監査テーブルはデータ削除を想定しておらず、トレーサビリティのために履歴は保持する方針です。
- 現在、strategy / execution / monitoring 部分は骨子のみで実装の拡張が期待されます。

## 今後の拡張案（参考）
- kabuステーション（実際の発注）連携の実装、約定コールバック対応
- Slack への通知・アラート機能の実装
- ストラテジーのプラグイン化・バージョニング管理
- CI 用のテスト・モック（J-Quants のモックサーバや VCR 的な仕組み）

---

この README はコードベースの現状（データ層・設定・監査層を中心）を反映しています。追加の機能や運用手順を実装する際は、.env.example や pyproject.toml／requirements.txt、リリースノート等も整備してください。