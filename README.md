# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ収集（J-Quants）、DuckDB によるローカル DB 管理、データ品質チェック、特徴量計算、ニュース収集、監査ログなど、戦略実行のための基盤機能を提供します。

---

## 主な特徴 (機能一覧)

- データ収集
  - J-Quants API からの株価日足・財務データ・マーケットカレンダー取得（ページネーション対応、レート制限・リトライ・トークン自動リフレッシュ対応）
- データ格納 / スキーマ管理
  - DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit レイヤ）
  - 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）を利用
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL の一括実行 API
- ニュース収集
  - RSS フィードの安全な取得（SSRF対策、gzip/サイズ上限、XML脆弱性対策）
  - 記事正規化、SHA-256 による記事ID生成、DuckDB への冪等保存、銘柄コード抽出
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、Zスコア正規化など（外部ライブラリに依存しない純 Python 実装）
- 監査ログ
  - シグナル→発注→約定までのトレーサビリティを保つ監査テーブルと初期化機能
- 設定管理
  - .env/.env.local からの自動読み込み（プロジェクトルート判定）、必須環境変数のラップ

---

## 必要条件 / 依存パッケージ

- Python 3.10+
  - （ソースで `X | None` などの型ヒントを使用しているため）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

※ 実行環境により追加パッケージ（ネットワークや API 連携のため）をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンする
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   # 開発インストール（パッケージとして使う場合）
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注周り）
     - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack 通知用トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live のいずれか（デフォルト: development）
     - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単なコード例）

以下は Python スクリプトや REPL での利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行
```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
res = pipeline.run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

3) ニュース収集ジョブ実行
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# 既知の銘柄コードセットを渡すと記事と銘柄の紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

4) 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
tgt = date(2024, 1, 4)

mom = calc_momentum(conn, tgt)              # モメンタム
vol = calc_volatility(conn, tgt)            # ボラティリティ/流動性
val = calc_value(conn, tgt)                 # バリュー（PER/ROE）
fwd = calc_forward_returns(conn, tgt)       # 将来リターン
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

5) Zスコア正規化
```python
from kabusys.data.stats import zscore_normalize

normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 主要モジュール一覧（簡単説明）

- kabusys.config
  - .env の自動読み込み・Settings ラッパー（必須 env のチェック）
- kabusys.data
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
  - schema.py         : DuckDB スキーマ定義・初期化
  - pipeline.py       : ETL パイプライン（差分取得・品質チェック）
  - news_collector.py : RSS ベースのニュース収集と保存
  - quality.py        : データ品質チェック
  - stats.py          : Zスコアなど統計ユーティリティ
  - calendar_management.py : マーケットカレンダー管理ユーティリティ
  - audit.py          : 監査ログスキーマと初期化
- kabusys.research
  - factor_research.py : ファクター計算（momentum, volatility, value）
  - feature_exploration.py : 将来リターン・IC・集計関数等
- kabusys.execution / kabusys.strategy / kabusys.monitoring
  - 実行・戦略・監視用のパッケージプレースホルダ（実装を拡張可能）

---

## ディレクトリ構成

（ソースに基づく主要ファイル抜粋）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ stats.py
   │  ├─ pipeline.py
   │  ├─ quality.py
   │  ├─ features.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ etl.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

---

## 運用上の注意 / ヒント

- 認証情報（J-Quants トークン等）は `.env` に保存するか、CI/運用環境のシークレット管理を利用してください。
- J-Quants API はレート制限（120 req/min）に注意。jquants_client モジュールは内部でスロットリングとリトライを行います。
- DuckDB ファイルは軽量ですがバックアップを定期的に行ってください。監査ログは別 DB に分けることが推奨されます（audit.init_audit_db を利用）。
- market_calendar が未取得の状態でもフォールバックで曜日ベース（平日を営業日）判定を行うため、カレンダーは早めに取得・維持してください。
- テストや CI で自動的な .env 読み込みを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献 / 拡張

- 新しいファクターや ETL のデータソースを追加するには、data モジュールに fetch/save の実装を追加し、pipeline にジョブを組み込む形が推奨です。
- execution や strategy パッケージは戦略実行用のインターフェースとして拡張できます（例: ブローカー固有のオーダー送信、ポジション管理）。
- テスト用に jquants_client の HTTP 呼び出しや news_collector._urlopen などをモックする設計になっています。

---

README はここまでです。利用にあたって具体的な実行スクリプトや追加の依存関係（例: HTTP クライアント、Slack 通知用ライブラリ等）が必要であれば、その用途に応じたサンプルを追記します。必要ならどの部分を詳述するか教えてください。