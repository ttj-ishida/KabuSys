# KabuSys — 日本株自動売買基盤 (README)

日本語ドキュメントです。本リポジトリは日本株向けのデータプラットフォームと戦略実行基盤を提供するライブラリ群です。DuckDB をデータストアに用い、J-Quants API や RSS ニュースを取り込み、特徴量生成→シグナル作成→発注/実行監視までのワークフローを支援します。

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL（差分取得・冪等保存）
- RSS ニュース収集と記事 → 銘柄マッピング
- 研究側で算出した「生ファクター」を正規化・合成して戦略用特徴量を作成
- 特徴量 + AI スコア を統合して売買シグナルを生成（BUY / SELL）
- 発注・約定・ポジション・監査ログ向けの DB スキーマとユーティリティ
- 市場カレンダー/営業日判定や統計ユーティリティ等の補助機能

設計上のポイント：
- DuckDB を永続ストレージとして利用（ローカルファイル / :memory:）
- 冪等性（ON CONFLICT / UPSERT）・トランザクションを重視
- ルックアヘッドバイアス回避（target_date 時点のデータのみ参照）
- 外部依存を最小化（標準ライブラリ + 必要最小限ライブラリ）

## 主な機能一覧

- data/
  - jquants_client: J-Quants からのデータ取得（レート制限・リトライ・トークンリフレッシュ対応）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS 収集、記事正規化、銘柄抽出・保存
  - schema: DuckDB スキーマ定義と初期化
  - calendar_management: 市場カレンダーの管理・営業日判定
  - stats / features: Zスコア正規化などの統計ユーティリティ
  - audit: シグナル→発注→約定までの監査ログスキーマ
- research/
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算・IC・統計サマリー等（研究用途）
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化・統合して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL を生成
- execution/ (発注層のインターフェースやステータス管理用の場所)
- monitoring/ (監視・Slack 通知などのユーティリティを配置想定)

## 要件（推奨）

- Python 3.10 以上（型ヒントで | を使用しているため）
- duckdb
- defusedxml
- （任意）その他標準ライブラリは不要

インストール例（仮: pip）:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトを editable install する場合
python -m pip install -e .
```

## 環境変数 / 設定

KabuSys は .env / .env.local / OS 環境変数から設定を読み込みます（プロジェクトルート判定は .git または pyproject.toml に依存）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）

その他（任意・デフォルトあり）：
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

環境変数が未設定で必須のものが参照された場合、Settings モジュールは ValueError を送出します。

## セットアップ手順（簡易）

1. リポジトリをクローンして Python 環境を準備
2. 依存ライブラリをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマ初期化

例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # data/ ディレクトリは自動作成されます
```

## 使い方（主要ワークフロー例）

以下はライブラリを直接呼ぶ Python の例です。実運用ではジョブスケジューラ（cron / Airflow 等）やコンテナ/VM 上のバッチで実行します。

1) DB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

3) 特徴量作成（research モジュールで算出した raw factor を正規化して features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date(2024, 1, 15))
print(f"built features: {count}")
```

4) シグナル生成（features + ai_scores → signals テーブルへ）
```python
from datetime import date
from kabusys.strategy import generate_signals
total = generate_signals(conn, target_date=date(2024, 1, 15), threshold=0.6)
print(f"signals generated: {total}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203","6758", ... }  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- generate_signals は features / ai_scores / positions を参照します。ai_scores は別プロセスで生成・挿入する想定です（AI モデル等）。
- ETL / save 系の関数は冪等で設計されています（ON CONFLICT DO UPDATE / DO NOTHING）。

## テスト・開発補助

- 自動 .env ロードを無効化してテストしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB をメモリで使いたい場合: `init_schema(":memory:")`
- ログレベルは環境変数 `LOG_LEVEL` で制御できます。

## ディレクトリ構成（主なファイル）

リポジトリの主要なパッケージ構成（src/kabusys 以下）を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings 管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（レート制限・リトライ）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - schema.py               — DuckDB スキーマ定義・init_schema()
    - news_collector.py       — RSS 取得・記事正規化・保存処理
    - calendar_management.py  — 市場カレンダー管理・営業日ユーティリティ
    - features.py             — features 用ユーティリティ（再エクスポート）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - audit.py                — 監査ログ（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features()
    - signal_generator.py     — generate_signals()
  - execution/                — 発注・実行層（将来的な実装想定）
  - monitoring/               — 監視・通知（Slack 等）

（実際のファイル・サブパッケージはリポジトリの内容に従います。上記は主要ファイルの抜粋です）

## 開発における設計・運用上の留意点

- データの整合性を優先し、DB 保存はトランザクションと冪等操作で行います。
- ルックアヘッドバイアス回避のため、各計算・判定は target_date 時点で入手可能なデータのみを扱います。
- API 呼び出しにはレート制限およびリトライを実装済みですが、運用では API 利用上限を監視してください。
- production (live) 環境では KABUSYS_ENV を `live` に設定し、ログや発注フローの監視を強化してください。

## お問い合わせ / 貢献

本 README はコードベースの主要機能を解説した概要ドキュメントです。詳細な仕様（StrategyModel.md / DataPlatform.md 等）や運用手順は別途ドキュメントを参照してください。Issue や PR は歓迎します。

---

以上。必要であれば各モジュールの利用例や API の詳細（引数・戻り値の表）を追加で生成します。どの箇所を詳しく記載したいか教えてください。