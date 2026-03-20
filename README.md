# KabuSys

日本株向けの自動売買基盤ライブラリ（研究用ファクター計算、ETL、特徴量生成、シグナル生成、ニュース収集、監査スキーマ等を含む）。  
本リポジトリは DuckDB を用いたローカルデータレイヤと、J‑Quants API / RSS 等からデータを取得するコンポーネント群を提供します。

---

## 概要

KabuSys は次の層を備えた日本株自動売買プラットフォームの基盤ライブラリです。

- Data layer（DuckDB）: 生データ、加工済みデータ、特徴量、実行ログを格納するスキーマ
- ETL（J‑Quants クライアント）: 株価・財務・カレンダー等の差分取得・保存（冪等）
- Research / Strategy: ファクター計算、Zスコア正規化、特徴量構築、シグナル生成
- News collector: RSS 取得・前処理・記事保存・銘柄抽出
- Audit / Execution schema: シグナル→発注→約定の監査トレーサビリティ用テーブル群

設計上の特徴:
- DuckDB を永続 DB として採用、DDL は冪等で実行可能
- J‑Quants API はレート制限・リトライ・トークン自動リフレッシュに対応
- 多くの処理は「日付単位で置換（DELETE -> INSERT）」するため冪等性を担保
- 外部依存を最小限にし、研究環境（research）と本番ロジックの分離を重視

---

## 主な機能一覧

- データ取得 / 保存
  - J‑Quants から日足（OHLCV）、財務情報、マーケットカレンダーを取得・保存
  - raw_prices / raw_financials / market_calendar などの raw layer を管理
- ETL（差分更新）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 最終取得日を基に差分で取得、バックフィル・品質チェックをサポート
- データスキーマ初期化
  - init_schema(db_path) で DuckDB に必要テーブルを作成
- 研究・特徴量
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - zscore_normalize：クロスセクションの Z スコア正規化
  - build_features：正規化・ユニバースフィルタを適用して features テーブルへ保存
- シグナル生成
  - generate_signals：features / ai_scores / positions を参照して BUY/SELL シグナルを生成・保存
  - Stop-loss、Bear レジーム抑制、重み付け補正等のルールを実装
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- 監査（audit）
  - signal_events / order_requests / executions 等の監査用テーブルを準備

---

## 動作要件（推奨）

- Python 3.10 以上（PEP 604 の型 | を使用）
- 必須パッケージ（主なもの）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, datetime, logging 等）

インストールはプロジェクトルートで通常の Python workflow に従ってください（例: pip install -e .）。requirements.txt がある場合はそちらを使用してください。

---

## 環境変数（.env）

自動的にプロジェクトルートの `.env` / `.env.local` が読み込まれます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（get_id_token で ID トークンを取得）
  - KABU_API_PASSWORD: kabuステーション API パスワード（execution 層で使用）
  - SLACK_BOT_TOKEN: Slack 通知用トークン
  - SLACK_CHANNEL_ID: Slack チャンネル ID
- 任意（デフォルトあり）
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 3.10+ を用意
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布に requirements.txt / pyproject.toml があればそれを利用）
4. リポジトリをパスにインストール（開発モード）
   - pip install -e .
5. .env をプロジェクトルートに作成（上記参照）
6. データベース初期化
   - 下記「使い方」を参照

---

## 使い方（基本例）

以下は Python REPL / スクリプト上での基本的なフロー例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も使用可
```

2) 日次 ETL 実行（J‑Quants から市場カレンダー/株価/財務を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を明示することも可能
print(result.to_dict())
```

3) 研究用ファクター計算 → 特徴量構築
```python
from kabusys.strategy import build_features
from datetime import date
cnt = build_features(conn, target_date=date(2024, 3, 20))
print(f"features upserted: {cnt}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n_signals = generate_signals(conn, target_date=date(2024, 3, 20))
print(f"signals written: {n_signals}")
```

5) ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効銘柄コードのセット（抽出に利用）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: new_count, ...}
```

6) J‑Quants からの直接フェッチ（テストやバッチ用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
records = fetch_daily_quotes(date_from=date(2024,3,1), date_to=date(2024,3,20))
# 保存は save_daily_quotes を通して行う
```

注意点:
- run_daily_etl 等は個々のステップで例外を捕捉しつつ継続する設計ですが、発生したエラーは ETLResult.errors に蓄積されます。
- J‑Quants へのリクエストは内部でレート制限・リトライを行います。ID トークンは自動リフレッシュされキャッシュされます。
- build_features / generate_signals は target_date 分を日付単位で DELETE→INSERT するため冪等です。

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（レート制限、リトライ、保存ユーティリティ）
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl / run_prices_etl 等）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - news_collector.py — RSS フェッチ・前処理・DB 保存・銘柄抽出
    - calendar_management.py — market_calendar の管理・営業日計算・カレンダー更新ジョブ
    - audit.py — 監査ログ（signal_events / order_requests / executions 等）
    - features.py — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility（prices_daily, raw_financials 参照）
    - feature_exploration.py — forward returns, IC, factor summary 等（研究用）
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（ユニバースフィルタ、正規化、features テーブルへ UPSERT）
    - signal_generator.py — generate_signals（final_score 計算、BUY/SELL 生成、signals テーブルへ保存）
  - execution/ — 発注・約定関連（現在はパッケージプレースホルダ）
  - monitoring/ — 監視・モニタリング関連（プレースホルダ）

（上記に加え、テストやドキュメント、設定ファイル等がルートに存在する想定）

---

## 開発・運用上の補足

- セキュリティ
  - news_collector は SSRF を防ぐためスキーム検査・リダイレクト先のプライベート IP 検査等を実施します。
  - defusedxml を利用して XML インジェクション攻撃を軽減しています。
- 冪等性
  - J‑Quants からの保存処理は ON CONFLICT / DO UPDATE を使い冪等性を担保します。
  - features / signals テーブルは日付単位で置換を行い、再実行が安全です。
- ロギング／監査
  - 各モジュールは logging を利用して動作を記録します。運用時は LOG_LEVEL を調整してください。
  - audit モジュールにより戦略→発注→約定のトレーサビリティを保持できます。
- テスト
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。
  - ネットワーク依存関数（_urlopen 等）はモックしやすく設計されています。

---

もし README に追加したい内容（例: CI のセットアップ、より詳細な API リファレンス、具体的な SQL スキーマドキュメント等）があれば教えてください。必要に応じてサンプルスクリプトや運用手順も作成します。