# KabuSys

日本株向けの自動売買（データ基盤＋戦略＋実行/監視）ライブラリ群です。  
このリポジトリは以下の層を備えたパイプライン・戦略実装を含みます：

- データ取得・ETL（J-Quants API 経由、DuckDB に永続化）
- ニュース収集（RSS → raw_news）
- ファクター計算（momentum / volatility / value 等）
- 特徴量構築（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL 判定）
- DuckDB スキーマ定義・監査ログ構造

バージョン: 0.1.0

---

## 主な機能

- データ取得
  - J-Quants API から日足（OHLCV）、財務データ、JPX カレンダーをページネーション対応で取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL / Data Platform
  - DuckDB スキーマ生成（raw / processed / feature / execution 層）
  - 差分更新（最終取得日からの差分 + バックフィル）
  - 品質チェックフック（quality モジュール経由）
- ニュース収集
  - RSS 取得（SSRF 対策・gzip 対応・XML の安全パース）
  - 記事正規化・ID（URL 正規化 → SHA-256）生成・銘柄抽出（4桁コード）
  - raw_news / news_symbols への冪等保存
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 戦略
  - 特徴量構築（build_features）：正規化・ユニバースフィルタ適用・features テーブルへ upsert
  - シグナル生成（generate_signals）：features + ai_scores を融合して final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込む
- 実行・監査（スキーマ）
  - signal_queue / orders / trades / executions / positions / audit テーブル群を含む

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法（X | None）等を使用）
- 必須パッケージ（一部例）
  - duckdb
  - defusedxml

実際の利用では上記に加え、J-Quants 用の資格情報・kabu API 認証等が必要です。

インストール例（任意の仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb defusedxml
# 開発用にパッケージを editable install する場合:
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。）

---

## 環境変数 / 設定

このライブラリは環境変数から設定値を読み込みます。自動でプロジェクトルートの `.env` / `.env.local` を読み込む機能があります（CWD に依存せず __file__ を基準に探索）。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須) — kabu API パスワード
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行環境 / ログ
  - KABUSYS_ENV (任意, デフォルト: development) — 有効値: development / paper_trading / live
  - LOG_LEVEL (任意, デフォルト: INFO) — 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL

必須変数が未設定の場合は Settings プロパティが ValueError を投げます（kabusys.config.Settings 経由）。

---

## セットアップ手順（最小）

1. リポジトリをクローンして仮想環境を作成
2. 必要パッケージをインストール（duckdb, defusedxml など）
3. .env を作成して必須の環境変数を設定
4. DuckDB スキーマを初期化してデータベースファイルを作成

例:
```python
# Python REPL / スクリプト 例
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("DB initialized:", conn)
```

---

## 使い方（代表的な API）

以下は最小限の使用例です。実運用ではログ設定や例外処理を追加してください。

- 日次 ETL の実行（価格・財務・カレンダーの差分取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {count}")
```

- RSS ベースのニュース収集
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を与えると記事に紐づく銘柄抽出を行います
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

- J-Quants からの取得と保存（プログラム的に）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection, init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

関数の戻り値や挙動の詳細は該当モジュールの docstring を参照してください（例: run_daily_etl は ETLResult を返します）。

---

## .env 読み込みの挙動と注意点

- 自動読み込み順序: OS 環境変数 > .env.local > .env
- `.env.local` は `.env` を上書きする（override=True）。
- OS 環境変数のキーは保護され、.env によって上書きされません。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env ファイルの書式は一般的な KEY=VALUE 形式をサポートします（export プレフィックスやクォート、コメントなどの扱いに対応）。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得/保存）
      - news_collector.py            — RSS 収集・記事抽出・保存
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - schema.py                    — DuckDB スキーマ定義・初期化
      - stats.py                     — zscore_normalize 等統計ユーティリティ
      - features.py                  — data 層の特徴量ユーティリティ（再エクスポート）
      - calendar_management.py       — market_calendar 管理ユーティリティ
      - audit.py                     — 監査ログスキーマ / 初期化ロジック
    - research/
      - __init__.py
      - factor_research.py           — momentum/volatility/value 計算
      - feature_exploration.py       — forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py      — build_features
      - signal_generator.py         — generate_signals
    - execution/                      — 発注・execution 層（最小実装 / プレースホルダ）
    - monitoring/                     — 監視周り（SQLite 等へ記録する想定）
- pyproject.toml / setup.cfg / requirements.txt など（存在すれば利用）

各モジュールは docstring に設計方針・処理フロー・注意点が詳細に記載されています。実装は DuckDB を中心に、発注周りは外部 API（kabu）への橋渡しが想定されています。

---

## 運用上の注意

- 実際の発注やライブ運用を行う場合、KABUSYS_ENV を `live` に設定し、十分なテスト（paper_trading も活用）を行ってください。
- ETL / API 呼び出しにはネットワーク制約やレート制限があるため、運用環境の監視・リトライ・アラートを設定してください。
- news_collector は外部 RSS を取得します。SSRF 対策や最大受信サイズなど安全措置を備えていますが、信頼できるソースのみを登録してください。
- DuckDB のファイルは定期バックアップを推奨します（特に監査ログ・取引履歴を保持する場合）。

---

## 開発・貢献

- 各モジュールの docstring を起点にユニットテストを追加してください。
- 依存パッケージや CI のセットアップはプロジェクトルートに配置してください（requirements.txt / pyproject.toml / tox / GitHub Actions 等）。
- セキュリティ関連（API トークン・秘密情報）は永続化・ログ出力に注意してください。

---

必要であれば README にサンプル .env.example やセットアップスクリプト、より詳細な CLI / systemd / cron の実行例（ETL スケジューリングや監視連携）を追加できます。どの部分を拡充したいか教えてください。