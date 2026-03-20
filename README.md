# KabuSys

日本株向けの自動売買（データプラットフォーム + 戦略）ライブラリです。  
DuckDB をデータレイヤに使い、J-Quants API / RSS ニュース等からデータを収集して特徴量を作成し、戦略シグナルを生成することを目的としています。

## 概要

このパッケージは以下のレイヤで構成されています。

- Data layer (DuckDB): 生データ / 整形済みデータ / 特徴量 / 発注・約定ログのスキーマを定義
- Data ingestion: J-Quants API クライアント、RSS ニュース収集器、ETL パイプライン
- Research: ファクター計算、特徴量探索（IC・将来リターン等）
- Strategy: 特徴量正規化（feature_engineering）とシグナル生成（signal_generator）
- Execution / Monitoring: 発注・監査・監視用スコープ（実装の骨格を含む）

設計上のポイント:
- 冪等性（DB への保存は ON CONFLICT で上書き/スキップ）
- ルックアヘッドバイアスに配慮した時点指定処理（target_date ベース）
- 外部依存は最小化（標準ライブラリ中心、必要最低限の外部モジュールのみ）

---

## 主な機能一覧

- DuckDB スキーマの初期化（data.schema.init_schema）
- J-Quants API クライアント（差分取得、ページネーション、リトライ、レート制御）
- 日次 ETL（run_daily_etl）: カレンダー、株価、財務データの差分取得および保存
- RSS ニュース収集と DB 保存（news_collector.run_news_collection, save_raw_news 等）
- ファクター計算（research.factor_research: momentum, volatility, value）
- 特徴量構築（strategy.feature_engineering.build_features）
- シグナル生成（strategy.signal_generator.generate_signals）
- 汎用統計ユーティリティ（data.stats.zscore_normalize）
- マーケットカレンダー管理（data.calendar_management）
- 監査ログ用スキーマ（data.audit）

---

## 必須要件 / 推奨環境

- Python 3.10+
- duckdb
- defusedxml

インストール例（仮の pyproject/セットアップがある前提）:
```bash
python -m pip install "duckdb" "defusedxml"
# 開発パッケージを編集インストールしている場合:
# pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みはプロジェクトルートに `.git` または `pyproject.toml` がある場合のみ動作）。

自動読み込みを無効にする（テスト等）:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルト付き:
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- その他 .env.local で開発用上書き可能

簡易 `.env` 例（実運用時は機密情報を適切に保護してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: Settings クラスは未設定の必須キーを参照すると ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ移動
2. Python 3.10+ 仮想環境を作成して依存パッケージをインストール
   - duckdb, defusedxml など
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

スキーマ初期化例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# :memory: を使う場合: init_schema(":memory:")
```

---

## 使い方（簡単な例）

以下はライブラリを呼び出す代表的な操作例です。実運用では適切なログ出力・例外処理・スケジューラと組み合わせてください。

- 日次 ETL を実行してデータを取得・保存する:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化済みの場合は get_connection
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量を構築（feature layer への書き込み）:
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成:
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {total}")
```

- ニュース収集ジョブ:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効な銘柄コードのセット（例: {"7203","6758",...}）
results = run_news_collection(conn, sources=None, known_codes=set(), timeout=30)
print(results)
```

- J-Quants からデータを直接フェッチして保存:
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

---

## API / モジュールのポイント

- config.Settings: 環境変数の取得と検証（必須値チェック、env/log level の検証）
- data.schema:
  - init_schema(db_path): スキーマ作成（冪等）
  - get_connection(db_path): 既存 DB への接続
- data.jquants_client:
  - レート制御、リトライ、トークン自動リフレッシュを備えた API クライアント
  - fetch_* / save_* 系で取得と保存を分離
- data.pipeline:
  - run_daily_etl: 日次差分 ETL + 品質チェック
- research.factor_research:
  - calc_momentum / calc_volatility / calc_value を提供
- strategy.feature_engineering.build_features:
  - research で計算した raw factor を統合・正規化して features テーブルへ UPSERT
- strategy.signal_generator.generate_signals:
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを signals テーブルへ保存
- data.news_collector:
  - RSS 取得・前処理・raw_news 保存・銘柄抽出（SSRF 対策 / XML 防御 / サイズ制限）

---

## ディレクトリ構成

主要ファイル（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他、quality 等が想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/
    - (監視・通知周りの実装想定)

README 中で触れている主な機能は上記ファイル群に実装されています。各モジュールには詳細なドキュメント文字列（docstring）が含まれているので、関数ごとの挙動・設計方針はソース内コメントを参照してください。

---

## 注意事項 / トラブルシューティング

- 環境変数が不足していると settings のプロパティ呼び出しで ValueError が発生します。エラーメッセージに従い .env を整備してください。
- DuckDB ファイルのパスは設定（DUCKDB_PATH）で指定できます。初回スキーマ作成時に親ディレクトリは自動作成されます。
- J-Quants API はレート制限（120 req/min）を守る実装ですが、外部 API の仕様や認証トークンの有効期限に依存します。401 が返った場合は自動で token をリフレッシュして再試行します。
- RSS フェッチは SSRF・XML ボム対策を実装していますが、外部ネットワークの可用性には依存します。
- 本ライブラリは研究・紙芝居（paper_trading）・実運用（live）モードを区別する設計です。KABUSYS_ENV を適切に設定してください。

---

## 参考 / 今後の拡張

- execution 層の broker 接続実装（kabuステーション API との実通信）
- リスク管理 / ポートフォリオ最適化モジュール
- 監視ダッシュボード・アラート連携（Slack 連携の具体実装）
- テストケース・CI（自動化）

---

ライブラリやドキュメントの改善要望、追加機能の提案があれば教えてください。