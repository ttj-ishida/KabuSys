# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDBベースのスキーマなどを備えたモジュール群を提供します。

主な設計方針：
- 研究（research）と本番（execution）を分離
- ルックアヘッドバイアスの排除（target_date 時点のデータのみを使用）
- DuckDB を用いたローカル DB（冪等保存 / トランザクション）
- 外部 API 呼び出しはレート制限・リトライ・トークンリフレッシュ対応

バージョン: 0.1.0

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レートリミット制御・リトライ・401時のトークン自動更新
- ETL パイプライン
  - 差分取得、backfill、品質チェック統合（日次ETL）
- データスキーマ
  - DuckDB 上に Raw / Processed / Feature / Execution 層テーブルを初期化
- 研究用モジュール
  - モメンタム、ボラティリティ、バリュー等ファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 特徴量加工（feature engineering）
  - ファクターの正規化（Z スコア）・ユニバースフィルタ・features テーブルへのUPSERT
- シグナル生成
  - features / ai_scores を統合して final_score を計算、BUY/SELL シグナルの作成・signals テーブルへの保存
  - Bear レジーム抑制、エグジット（ストップロス／スコア低下）
- ニュース収集
  - RSS フィード取得（SSRF 対策、トラッキング除去、gzip サイズ制限）
  - raw_news テーブルへの冪等保存、銘柄コード抽出と紐付け
- 監査/log（audit）設計（監査用DDLを含む）

---

## 前提・依存関係

推奨 Python バージョン: 3.10 以上

主な Python パッケージ（最低限）:
- duckdb
- defusedxml

（プロジェクトの pyproject.toml / requirements.txt を参照して下さい。上記はコードから明示的に使用されているライブラリです。）

---

## 環境変数 / 設定

KabuSys は環境変数（または .env ファイル）から設定を読み込みます。自動ロード順序は以下：

1. OS 環境変数
2. プロジェクトルートの `.env.local`（存在すれば上書き）
3. プロジェクトルートの `.env`（未設定のキーのみセット）

※ 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。プロジェクトルートはこのパッケージファイルの親ディレクトリから `.git` または `pyproject.toml` を探索して決定します。

必須の主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

オプション（デフォルト値あり）:
- KABUSYS_ENV: 実行環境 {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env 例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. パッケージのインストール
   - プロジェクトに pyproject.toml/setup がある場合:
     ```
     pip install -e .
     ```
   - 必要な依存ライブラリを個別にインストール:
     ```
     pip install duckdb defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成して必要なキーを設定
   - もしくは CI / 実行環境で環境変数を設定

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     # conn は duckdb 接続オブジェクト
     ```

---

## 使い方（代表的な操作例）

以下はライブラリ API を直接呼ぶ最小例です。実際はジョブスケジューラ（cron / Airflow 等）や CLI ラッパー経由で運用することを想定しています。

- 日次 ETL の実行
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量の作成（ある日付について）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, date(2024, 1, 10))
print("upserted features:", count)
```

- シグナル生成（ある日付について）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, date(2024, 1, 10))
print("signals generated:", n)
```

- ニュース収集ジョブの実行
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "7201"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants のデータ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って自動取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

ログ出力レベルは環境変数 `LOG_LEVEL` で制御してください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要モジュールと説明です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS 収集、記事正規化、DB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - schema.py               — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py                — zscore_normalize 等統計ユーティリティ
    - features.py             — data.stats の再エクスポート
    - calendar_management.py  — market_calendar の運用ユーティリティ
    - audit.py                — 監査ログ向け DDL（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py      — momentum/volatility/value の計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — features 作成（build_features）
    - signal_generator.py     — generate_signals（BUY/SELL ロジック）
  - execution/
    - __init__.py            — 発注・約定関連（空のパッケージプレースホルダ）
  - monitoring/              — 監視用コード（別途実装想定）

（上記は現行コードベースの主なモジュール。追加のユーティリティやドキュメントが存在する場合があります。）

---

## 運用に関する注意事項

- 本リポジトリには実際の売買 API 呼び出しやマネーを動かすコードのラッパー（execution 層）は最小化または分離されています。実運用で発注を行う場合は十分なレビュー・テスト・リスク管理が必須です。
- J-Quants のレート制限（120 req/min）や API のレスポンスに対するリトライ・バックオフロジックは実装されていますが、実環境の運用ではジョブ間隔や並列度に注意してください。
- ニュース収集では SSRF・XML Bomb 等の安全対策（defusedxml、リダイレクト検査、レスポンスサイズ制限）を行っていますが、外部フィードの扱いは引き続き慎重に。
- 環境により db ファイルのパスや保存ポリシー（バックアップ、排他ロック）を検討してください。DuckDB ファイルはファイルベースのため共有アクセスの設計に注意が必要です。

---

## 開発 / 貢献

- バグ修正や機能追加の際はユニットテスト・データ整合性テストを追加してください。
- テスト実行・CI の整備を推奨します（DuckDB のインメモリ接続を活用して高速なテストが可能です）。
- セキュリティ上の注記: API トークンやパスワードをリポジトリに含めないでください。`.env` は .gitignore に追加して管理してください。

---

README はここまでです。必要であれば以下の追加情報を作成します：
- .env.example のフルテンプレート
- CLI ラッパー（簡易コマンド）の雛形
- 運用手順（cron / systemd / Airflow 例）
- 詳細な DB スキーマ説明（各テーブルの列説明ドキュメント）

どれを追加しましょうか？