# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、特徴量計算、戦略シグナル生成、ニュース収集、監査ログ／スキーマ定義など、研究〜本番運用までの主要機能を含みます。

---

## プロジェクト概要

KabuSys は以下のレイヤーを持つ設計になっています。

- Data Layer: J-Quants API からの生データ取得、DuckDB への保存（raw / processed / feature / execution 層）
- Research Layer: ファクター計算・特徴量探索用ユーティリティ（ルックアヘッドバイアス対策を重視）
- Strategy Layer: 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- Execution / Monitoring: 発注・約定・ポジション管理や監査ログ用スキーマ（実装の一部／骨組み）

設計方針の要点:
- データ取得は冪等（ON CONFLICT ベース）で保存
- API レート制限やリトライ、トークン自動リフレッシュを実装
- DuckDB を中心に、軽量で高速な分析・運用を想定
- 研究コードと本番コードの分離（ルックアヘッド排除）

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（jquants_client）：日足・財務・マーケットカレンダー取得、保存用関数
  - ETL パイプライン（data.pipeline）：差分取得、backfill、品質チェック、日次ジョブ
  - スキーマ初期化（data.schema）：DuckDB のテーブル定義と初期化

- データ処理 / 分析
  - ファクター計算（research.factor_research）：Momentum, Volatility, Value など
  - 将来リターン / IC / 統計サマリー（research.feature_exploration）
  - 汎用統計ユーティリティ（data.stats）：Z スコア正規化など

- 特徴量 / シグナル
  - 特徴量構築（strategy.feature_engineering）：research の生ファクターを正規化して features テーブルへ UPSERT
  - シグナル生成（strategy.signal_generator）：features と ai_scores を統合して BUY / SELL を生成し signals テーブルへ書き込み

- ニュース収集
  - RSS 収集・正規化（data.news_collector）：SSRF 防止、gzip 制限、記事 ID のハッシュ化、銘柄抽出、DB 保存

- カレンダー管理
  - market_calendar の取得・営業日判定・next/prev_trading_day（data.calendar_management）

- 監査 / トレーサビリティ
  - signal / order / execution の監査テーブル（data.audit）

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の `X | None` などの構文を使用）
- 必須パッケージの例（環境に応じて追加してください）:
  - duckdb
  - defusedxml
- （プロジェクトで pyproject.toml / requirements.txt を用意している想定です。なければ上記を適宜 pip でインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトルートに pyproject.toml があれば:
pip install -e .
```

---

## 環境変数（必須・任意）

config.Settings で参照される主要な環境変数：

必須（Settings._require により未設定で例外になります）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層を使う場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト "INFO"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH — 監視 DB（デフォルト "data/monitoring.db"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で .env ファイルを読み込まなくなります（テスト用途）

プロジェクトルートに .env / .env.local があれば自動で読み込みます（.git または pyproject.toml をプロジェクトルート検出基準に使用）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（例: duckdb, defusedxml など）
4. 必要な環境変数を設定（または .env を作成）
5. DuckDB スキーマの初期化

例（UNIX シェル）:
```bash
git clone <repo-url> kabusys
cd kabusys
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# 環境変数設定（例）
export JQUANTS_REFRESH_TOKEN="xxxx"
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_CHANNEL_ID="C01234567"

# スキーマ初期化（デフォルト data/kabusys.duckdb に作成）
python - <<'PY'
from kabusys.config import settings
from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)
print("Initialized:", settings.duckdb_path)
conn.close()
PY
```

自動で .env を読み込む場合、プロジェクトルートに `.env` / `.env.local` を配置してください。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表的な操作例）

以下はライブラリを使って基本的なワークフロー（DB初期化 → ETL → 特徴量 → シグナル生成）を実行する例です。

1) スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 研究系ファクターから特徴量を構築（features テーブルに保存）
```python
from datetime import date
from kabusys.strategy import build_features

target = date(2024, 1, 15)
count = build_features(conn, target)
print("features upserted:", count)
```

4) シグナル生成（features / ai_scores / positions を参照して signals テーブルへ）
```python
from kabusys.strategy import generate_signals

signals_count = generate_signals(conn, target_date=target)
print("signals written:", signals_count)
```

5) ニュース収集ジョブの実行（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes を渡すとテキスト内の銘柄コード抽出で紐付けを行います
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

ログや例外は各モジュールが出力します。自動で Slack 通知機能等がある場合は、環境変数等を整えてください（Slack トークン等）。

---

## 開発／テストのヒント

- 自動で .env を読み込む機能はテストで邪魔になることがあるため、テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- API 呼び出し部分（jquants_client.fetch_*、news_collector._urlopen 等）はモック可能に設計されています（テスト時に外部アクセスを切る）。
- DuckDB の接続は `:memory:` 指定でインメモリ DB を利用できます（ユニットテストに便利）。

---

## ディレクトリ構成

主要ファイル（src/kabusys 以下、抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント + 保存関数
    - news_collector.py               — RSS 収集・前処理・保存
    - schema.py                       — DuckDB スキーマ定義 / init_schema
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - stats.py                        — zscore_normalize 等統計ユーティリティ
    - calendar_management.py          — market_calendar 管理 / 営業日判定
    - audit.py                        — 監査ログテーブル DDL（signal_events 等）
    - features.py                     — data.stats の公開ラッパー
  - research/
    - __init__.py
    - factor_research.py              — momentum / volatility / value の計算
    - feature_exploration.py          — calc_forward_returns, calc_ic, factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py          — features テーブル用の正規化／アップサート
    - signal_generator.py             — final_score 計算・BUY/SELL 生成
  - execution/                         — 発注・実行周り（パッケージ空の可能性あり）
  - monitoring/                        — 監視系モジュール（存在する場合）

（実際のツリーはリポジトリ内のファイルを参照してください。README は抜粋構成の例です。）

---

## 注意事項（運用上のポイント）

- J-Quants API のレート制限・リトライは jquants_client に実装されています。大量取得・バックフィルの際は注意してください。
- ルックアヘッドバイアスを防ぐため、戦略・特徴量計算は target_date 時点以下のデータのみ参照する設計です。外部からデータを投げる場合もこの方針に従ってください。
- DuckDB の外部キー制約や機能はバージョン差異で挙動が異なる可能性があります（README 内スキーマ注記をご参照ください）。
- 本リポジトリは研究・ペーパートレード・本番を想定した設計になっています。実際の資金を動かす前に十分なテストを行ってください。

---

この README はコードベースの主要機能と使い方の概要を示しています。より詳細な設計仕様（StrategyModel.md、DataPlatform.md、DataSchema.md 等）がリポジトリに含まれている想定ですので、実運用時にはそちらも参照してください。