# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README

このドキュメントはコードベース（src/kabusys 以下）の主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL・特徴量生成・シグナル生成・ニュース収集・監査ログなどを含む、自動売買システムのコアライブラリです。  
主な設計方針は以下です。

- DuckDB を用いたローカルデータレイク（Raw / Processed / Feature / Execution レイヤー）
- J-Quants API（株価・財務・カレンダー）との差分 ETL（レート制限・リトライ対応）
- 研究用ファクター計算（momentum / volatility / value 等）と Z スコア正規化
- 戦略用シグナル生成（複数コンポーネントの重み付け）とエグジット判定
- RSS 取得によるニュース収集と銘柄紐付け（SSRF/サイズ制限/トラッキング除去）
- 監査ログによるシグナル→発注→約定のトレーサビリティ

コードは src/kabusys 以下にモジュール化されています。

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
- Data（データ層）
  - J-Quants クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - DuckDB スキーマ定義 / 初期化（init_schema）
  - ETL パイプライン（差分更新、バックフィル、品質チェック）
  - ニュース収集 & 保存（RSS パース、前処理、銘柄抽出）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - 統計ユーティリティ（Z スコア正規化 等）
- Research（研究用）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）、ファクターサマリー
- Strategy（戦略層）
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals: BUY/SELL の判定、Bear レジーム判定、重み付け）
- Execution / Audit（実装方針とスキーマ）
  - 実行層のテーブル（signals, orders, trades, positions 等）
  - 監査用テーブル（signal_events, order_requests, executions）設計

---

## 必要条件 / 依存関係

- Python 3.10 以上（型注釈の「|」構文を使用）
- 主要ライブラリ（最低限）:
  - duckdb
  - defusedxml

インストール例（仮）:
```
pip install duckdb defusedxml
```

パッケージとしてローカルインストールする場合:
```
pip install -e .
```
（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください）

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml の位置）を探して `.env` → `.env.local` の順に読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD：kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN：Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID：Slack チャンネル ID（必須）

その他（任意 / デフォルトあり）:
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト：development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト：INFO）

.env の例（.env.example を参照して作成してください）:
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数が不足していると Settings プロパティが ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <このリポジトリのURL>
   cd <リポジトリ>
   ```

2. Python 環境の準備（仮想環境推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt    # もし requirements.txt があれば
   # または最低限:
   pip install duckdb defusedxml
   ```

4. .env をプロジェクトルートに作成
   - .env.example を参考に必須項目を設定してください。
   - 開発時は .env.local を使ってローカル上書きも可能（.env.local は .env を上書きします）。

5. DuckDB スキーマ初期化（Python から実行）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   - ":memory:" を渡すとインメモリ DB を使用します。
   - 必要に応じて parent ディレクトリは自動作成されます。

---

## 基本的な使い方（コード例）

以下は代表的なワークフローの例です。日付は datetime.date を使用します。

- 初期化と日次 ETL
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の生成
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2024, 1, 5))
print(f"features upserted: {count}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

num = generate_signals(conn, target_date=date(2024, 1, 5), threshold=0.6)
print(f"signals generated: {num}")
```

- ニュース収集（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "8306"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants データ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from datetime import date

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ログ・デバッグ

- ログレベルは環境変数 `LOG_LEVEL` で指定できます（デフォルト INFO）。
- 開発環境では `KABUSYS_ENV=development` を設定して実行してください。
- 自動で .env ファイルを読み込む処理は、テスト等の目的で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化可能です。

---

## よくあるトラブルと対処

- ValueError: 環境変数が未設定
  - 必須の環境変数（JQUANTS_REFRESH_TOKEN 等）を .env に設定してください。

- DuckDB のテーブルがない / 欠損
  - init_schema() を実行してスキーマを作成してください。

- ネットワーク / API エラー
  - J-Quants の認証トークン切れ時は jquants_client が自動でトークン更新を行い、リトライします。ただし refresh token 自体が無効な場合は手動で更新が必要です。

---

## ディレクトリ構成（主要ファイル）

概要的なツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（取得 + 保存）
    - news_collector.py              -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 他）
    - features.py                    -- zscore 再エクスポート
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py         -- カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                       -- 監査ログ用スキーマ / DDL
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py         -- IC / 将来リターン / サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         -- features の構築（正規化・フィルタ）
    - signal_generator.py            -- final_score 計算 / BUY/SELL 判定
  - execution/                       -- 発注・実行に関するモジュール（雛形）
  - monitoring/                      -- 監視・モニタリング層（存在する場合）

（実際のファイルはリポジトリ内の src/kabusys を参照してください）

---

## 開発・貢献

- 型注釈と単体テストを重視している設計です。ユニットテスト・CI の追加を歓迎します。
- .env.local はローカルの上書き用に使用してください（秘匿情報は環境変数やシークレット管理を推奨）。

---

以上が README の簡易版です。必要であれば、インストール手順（pyproject.toml / setup.cfg / requirements.txt に基づく）や実行スクリプト（例: CLI ラッパー）の追加、各モジュールの API リファレンス（引数・戻り値の詳細）を追記できます。どのセクションを詳しくしたいか教えてください。