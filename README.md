# KabuSys

日本株を対象とした自動売買プラットフォームのコアライブラリ（ライブラリ未完成・研究/プロダクション向けモジュール群）

短い概要：
- データ取得（J-Quants）→ DuckDB 保存（冪等）→ 品質チェック → 特徴量作成 → シグナル生成、というワークフローを Python API として提供します。
- 研究用のファクター計算・探索ユーティリティと、プロダクション想定の ETL / カレンダー管理 / ニュース収集 / 監査テーブル定義が含まれます。

バージョン: pkg の __version__ を参照してください（例: 0.1.0）。

---

## 主な機能

- 環境変数/設定管理
  - .env/.env.local をプロジェクトルートから自動読み込み（OS 環境変数優先、必要に応じて自動無効化可能）
  - 必須設定はアクセス時に検査してエラーを出す

- データ取得・保存（J-Quants）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーを API から取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等に保存（ON CONFLICT/UPSERT）

- ETL パイプライン
  - 差分取得（最終取得日とバックフィルの考慮）、品質チェックの統合
  - 日次 ETL エントリポイント（run_daily_etl）

- スキーマ管理
  - DuckDB 用のデータモデル（Raw / Processed / Feature / Execution / Audit）
  - init_schema でスキーマ初期化

- 特徴量（feature）生成
  - research の生ファクターを正規化・結合して features テーブルへ保存（build_features）

- シグナル生成
  - features + ai_scores を組み合わせ final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存（generate_signals）
  - Bear レジーム抑制、売買のエグジット判定（ストップロス等）を実装

- ニュース収集
  - RSS フィード収集・前処理・記事ID生成（正規化 URL の SHA-256 短縮）・raw_news 保存、銘柄抽出と紐付け

- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（Spearman）計算、ファクターの統計サマリー

- 汎用統計ユーティリティ
  - クロスセクション Z スコア正規化（data.stats.zscore_normalize）

---

## 必要条件（例）

- Python 3.10+
- duckdb
- defusedxml
- （ネットワークアクセス先）J-Quants API の利用資格（refresh token 等）

実際のプロジェクトでは pyproject.toml / requirements.txt を使って依存関係を管理してください。最低限以下パッケージをインストールしてください（例）:

pip:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発時: pip install -e .
```

---

## 環境変数 / 設定

kabusys.config.Settings で利用される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注層利用時）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...）（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト用途など）

.env ファイルはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）から自動読み込みされます。優先順位: OS 環境 > .env.local > .env。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（開発用の最小手順）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（duckdb, defusedxml 等）
4. 環境変数を設定（.env をプロジェクトルートに作る）
5. DuckDB スキーマを初期化

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必要ならパッケージを編集可能インストール
pip install -e .
# .env を作成（上記参照）
```

Python でスキーマ初期化:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Settings.duckdb_path プロパティで Path を返します
conn = init_schema(settings.duckdb_path)
```

メモ:
- テストや一時実行では db_path に ":memory:" を渡してインメモリ DB を使えます。
- init_schema は親ディレクトリがなければ自動作成します。

---

## 使い方（主要 API の例）

基本的なワークフロー例（日次 ETL → 特徴量作成 → シグナル生成）:

```python
from datetime import date
import duckdb

from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 日次 ETL（今日の市場データ取得・保存）
etl_result = run_daily_etl(conn, target_date=date.today())
print(etl_result.to_dict())

# 特徴量ビルド（features テーブルへ書き込み）
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")

# シグナル生成（signals テーブルへ書き込み）
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

ニュース収集を実行する例:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出に使う既知コード集合（例: prices_daily から取得）
known_codes = {row[0] for row in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

J-Quants の生データを直接保存する例:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

設定をテストで差し替えたい場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にできます
- jquants_client の id_token を外部から注入してテスト可能（関数引数で受け取れるものがある）

ログは標準の logging を使用します。LOG_LEVEL を環境変数で指定してください。

---

## ディレクトリ構成（主要ファイル）

パッケージルート: src/kabusys/

主なモジュール:
- kabusys/
  - __init__.py
  - config.py                           — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント + 保存関数
    - news_collector.py                 — RSS 収集・前処理・DB 保存
    - schema.py                         — DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py            — 市場カレンダー管理・営業日ユーティリティ
    - features.py                       — features 関連公開（zscore 再エクスポート）
    - stats.py                          — zscore_normalize 等統計ユーティリティ
    - audit.py                          — 監査ログ用スキーマ定義
    - (その他: quality モジュールは参照されるがここに未表示の可能性あり)
  - research/
    - __init__.py
    - factor_research.py                 — モメンタム/ボラティリティ/バリューなど
    - feature_exploration.py             — 将来リターン計算・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py             — features を作成するワークフロー
    - signal_generator.py                — final_score 計算と signals 生成
  - execution/
    - __init__.py                        — 発注/実行層（将来的に拡張）
  - monitoring/                          — 監視・モニタリング周り（存在宣言のみ）

上記以外にも補助ユーティリティや未表示のサブモジュールが存在する場合があります。

---

## 注意事項 / 実運用メモ

- Look-ahead バイアス対策:
  - 戦略モジュールは target_date 時点のデータのみを参照する設計になっています（将来データの混入を防止）。
  - API データ取得時には fetched_at を UTC で記録し、データが「いつ利用可能になったか」を追跡可能にしています。

- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT / DO UPDATE / DO NOTHING を使った冪等設計です。

- テスト:
  - DB を ":memory:" にすればインメモリでスキーマ初期化 → 単体テストが可能です。
  - 環境変数自動ロードはテストで邪魔になる場合があるため KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。

- 実際の発注（kabuステーション連携）を行う場合は、さらに認証・送信・エラーハンドリングの層を実装する必要があります（execution 層は拡張点）。

---

## さらに読む / ドキュメント参照（想定）

リポジトリには README のほかに以下のドキュメント（参照実装に基づく想定）が存在する想定:
- DataPlatform.md
- StrategyModel.md
- その他設計書（ETL/監査/カレンダー定義）

これらが存在する場合は併せて参照してください。

---

何か特定の操作（DB スキーマの詳しいカラム説明、ETL のトラブルシューティング、あるいは実行用スクリプトの追加）について README に追記したい点があれば教えてください。必要に応じてサンプルスクリプトや運用手順も追加します。