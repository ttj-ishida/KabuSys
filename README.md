# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をコアにしたデータレイク、J‑Quants からのデータ取得、品質チェック、特徴量計算、ニュース収集、監査ログなどを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の目的で設計された内部ライブラリです。

- J‑Quants API から株価・財務・マーケットカレンダーを安全に取得して DuckDB に保存する ETL
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用のファクター（モメンタム／バリュー／ボラティリティ等）計算ユーティリティ
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- 発注・戦略・監視関連の枠組み（モジュール分割済み）

設計上の特徴：
- DuckDB を用いた冪等な保存（ON CONFLICT ... DO UPDATE / DO NOTHING）
- J‑Quants のレート制御・リトライ・トークンリフレッシュ実装
- 外部依存を最小化した実装（ただし DuckDB / defusedxml 等は必要）
- Research 環境では本番発注 API にアクセスしない分離設計

---

## 主な機能一覧

- data:
  - jquants_client: J‑Quants API クライアント（ページネーション・リトライ・トークン管理）
  - pipeline: 日次 ETL（prices / financials / calendar）と品質チェックの統合
  - schema / audit: DuckDB スキーマ初期化（Raw/Processed/Feature/Execution 層、監査ログ）
  - news_collector: RSS 取得 → 正規化 → DuckDB に保存、銘柄抽出
  - quality: データ品質検査（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
- research:
  - factor_research: momentum / value / volatility の計算
  - feature_exploration: 将来リターン計算 / IC（情報係数） / 統計サマリー
- 設定管理: 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）
- 監査/実行周りのスキーマ・ユーティリティ

---

## 前提条件

- Python 3.10 以上（型アノテーションに | を使用）
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

上記は最低限。実行環境に合わせて追加のパッケージ（Slack クライアント等）が必要になる場合があります。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数・設定

このプロジェクトは .env または OS 環境変数から設定を読み込みます（自動ロード機能あり）。  
自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（README 用に抜粋）:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB 等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定値の取得例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # 必要に応じて他パッケージを追加
   ```

3. 環境変数を準備（.env を作成）
   - リポジトリルートに .env を置くと自動で読み込まれます
   - または環境変数として設定してください

4. DuckDB スキーマ初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # これで必要テーブルが作成されます（冪等）
   ```

5. 監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 基本的な使い方

以下に主な利用例を示します。

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 事前に有効コードを用意しておく
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- J‑Quants からの日足・財務取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使って取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
financials = fetch_financial_statements(id_token=token)
```

- 研究用ファクター計算
```python
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = get_connection(settings.duckdb_path)
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# 例: calc_ic を用いたファクター評価
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- Zスコア正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, columns=["mom_1m","mom_3m","ma200_dev"])
```

---

## 運用上の注意・ベストプラクティス

- J‑Quants の API レート（120 req/min）遵守が組み込まれていますが、バッチ設計側でもスロットリング方針を検討してください。
- 本番口座（live）モードで実行する際は `KABUSYS_ENV=live` を設定し、発注・監視モジュールに特別な保護を入れてください（リスク管理、二重発注防止）。
- テストや CI で環境変数の自動ロードが不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルのバックアップ・バージョン管理や権限管理を忘れずに（特に監査 DB）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／モジュールの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py: パッケージ定義（version 等）
  - config.py: 環境変数 / 設定管理（.env 自動読み込み、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py: J‑Quants API クライアント（取得 & DuckDB 保存補助）
    - news_collector.py: RSS 取得・正規化・DB 保存・銘柄抽出
    - schema.py: DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - pipeline.py: 日次 ETL フロー（差分取得・保存・品質チェック）
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py: 統計ユーティリティ（zscore_normalize など）
    - calendar_management.py: market_calendar の管理・営業日判定
    - audit.py: 監査ログ（signal/order/execution）スキーマ初期化
    - etl.py: ETLResult の公開（エイリアス）
  - research/
    - __init__.py: 研究用 API の公開
    - factor_research.py: momentum/value/volatility の計算
    - feature_exploration.py: 将来リターン、IC、summary、rank 等
  - strategy/: 戦略関連（骨組み）
  - execution/: 発注 / 約定処理（骨組み）
  - monitoring/: 監視用モジュール（骨組み）
- README.md: （本ファイル）
- .env.example: 環境変数サンプル（プロジェクトルートに配置して使用）

（実際のリポジトリではさらにテスト・ドキュメント・CI 設定ファイル等が含まれる場合があります）

---

## サポート / 追加情報

- コード内 docstring に各関数の使用法・戻り値の仕様が記載されています。利用時は docstring を参照してください。
- DuckDB の SQL 実行結果は Python 側で型変換されるため、date / datetime の扱いに注意してください（関数は date オブジェクトや ISO 文字列の取り扱いを考慮しています）。
- セキュリティ: news_collector は SSRF 対策・gzip bomb 対策・XML パースの堅牢化を行っていますが、実運用ではプロキシ / ネットワークレベルの追加制御を推奨します。

---

この README はこのコードベースの概要・導入ガイド・代表的な使い方を簡潔にまとめたものです。詳細は各モジュールの docstring を参照してください。