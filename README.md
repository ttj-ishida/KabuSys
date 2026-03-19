# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査／スキーマ管理など、戦略実装から実行レイヤまでを想定した機能を提供します。

Version: 0.1.0

---

## 概要

このリポジトリは以下の責務を持つモジュール群で構成されています。

- J-Quants API からの市場データ（株価・財務・カレンダー）取得と保存（DuckDB）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- リサーチ／ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量（features）生成と正規化
- シグナル生成（BUY / SELL）ロジック
- ニュース収集（RSS）と銘柄紐付け
- DuckDB スキーマ定義と監査ログテーブル
- 簡易な設定（環境変数経由）

設計方針として、ルックアヘッドバイアス回避、冪等性（idempotency）、外部ライブラリへの過度な依存回避（標準ライブラリ中心）を重視しています。

---

## 主な機能一覧

- data/jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークンリフレッシュ、RateLimit 制御）
- data/schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
- data/pipeline: 日次 ETL（差分取得、backfill、品質チェック）
- data/news_collector: RSS 収集、前処理、DB 保存、銘柄抽出（SSRF 対策、gzip 対応、XML 安全パース）
- research/factor_research: Momentum / Volatility / Value 等のファクター計算
- research/feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/feature_engineering: 生ファクターの統合・Zスコア正規化・features テーブル保存
- strategy/signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- config: 環境変数管理（.env 自動読み込み、必須チェック）
- audit: 監査ログ用テーブル定義（signal_events / order_requests / executions 等）

---

## 前提条件

- Python 3.10+
- DuckDB（Python パッケージ）
- defusedxml（RSS XML の安全なパースに使用）
- 標準ライブラリ（urllib, datetime, logging 等）

推奨インストールコマンド（仮の requirements）:

```bash
python -m pip install duckdb defusedxml
```

パッケージ化されている場合はソースルートで:

```bash
python -m pip install -e .
```

（本リポジトリに requirements.txt / pyproject.toml がある場合はそちらに従ってください）

---

## 環境変数（重要）

プロジェクトは環境変数から設定を読み込みます（`.env` / `.env.local` をサポート）。自動読み込みはルート（.git または pyproject.toml があるディレクトリ）を検出して行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API の Base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

設定が必要なキーが未設定の場合、config.Settings のプロパティが ValueError を投げます（例: settings.jquants_refresh_token）。

---

## セットアップ手順

1. Python 環境準備（仮想環境推奨）

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. 依存パッケージのインストール

```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# またはプロジェクトの packaging を用意している場合:
# python -m pip install -e .
```

3. 環境変数を設定

ルートに `.env` を作成（`.env.example` を参照して作る想定）。最低限 JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を設定してください。

4. DuckDB スキーマ初期化（デフォルト DB パスを使用する場合）

Python REPL またはスクリプトで:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

またはメモリ DB でテスト:

```python
conn = init_schema(":memory:")
```

---

## 使い方（簡易ガイド）

以下は代表的なワークフロー例です。実運用スクリプトは必要に応じて作成してください。

1) データベース初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量（features）ビルド

```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date(2025, 1, 15))
print(f"built features: {count}")
```

4) シグナル生成

```python
from kabusys.strategy import generate_signals
from datetime import date

num = generate_signals(conn, target_date=date(2025, 1, 15))
print(f"signals generated: {num}")
```

5) ニュース収集ジョブ（RSS）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(saved_map)
```

6) カレンダー更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- run_daily_etl 等は内部でエラーをログに残しつつ可能な限り処理を続行します。戻り値（ETLResult）で結果・品質問題・エラーを確認してください。
- DuckDB に対する書き込みはモジュール内でトランザクション管理（BEGIN / COMMIT / ROLLBACK）しています。

---

## 開発・テストのヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に実施します。テスト時に自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- DuckDB のインメモリ DB（":memory:"）はユニットテストで便利です。
- news_collector はネットワーク・SSRF 対策やレスポンスサイズ制限を実装しています。外部 URL を使う場合はテスト用のスタブサーバを用意するか、fetch_rss をモックしてください。
- J-Quants API 呼び出しは rate limit と retry ロジックを備えていますが、テスト時は id_token をモック注入することを検討してください（jquants_client._get_cached_token 等を置換）。

---

## ディレクトリ構成

主要なファイル・モジュールは以下の通りです（簡易ツリー）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py          — RSS 収集・前処理・保存
    - schema.py                  — DuckDB スキーマ定義／初期化
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                — 日次 ETL パイプライン
    - calendar_management.py     — 市場カレンダー管理
    - features.py                — data.stats の再エクスポート
    - audit.py                   — 監査ログテーブル DDL
  - research/
    - __init__.py
    - factor_research.py         — momentum/volatility/value の計算
    - feature_exploration.py     — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py     — features テーブル生成
    - signal_generator.py        — final_score -> signals テーブル生成
  - execution/                    — 発注・ブローカー連携層（パッケージ準備）
  - monitoring/                   — 監視・メトリクス（準備）
- data/                           — デフォルトのデータ格納先（例: data/kabusys.duckdb）
- .env, .env.local, .env.example  — 環境変数サンプル（プロジェクトルートに配置）

（上記はコードベースから抽出した代表ファイルです）

---

## ロギングとデバッグ

- モジュールは標準ライブラリの `logging` を使用します。`LOG_LEVEL` 環境変数でログレベルを制御できます（デフォルト: INFO）。
- ETL や収集処理で詳細デバッグが必要な場合は `LOG_LEVEL=DEBUG` を設定してください。

---

## 注意事項

- 本ライブラリは実際の証券会社への発注処理を含むよう設計されていますが、実際のブローカー連携（execution 層の実装）や運用監査・リスク管理の整備は別途必要です。
- 実資金で運用する前に paper_trading 環境で十分に検証してください（KABUSYS_ENV）。
- RSS / HTTP の取り扱いに関しては SSRF や XML 攻撃に留意して設計していますが、外部入力を扱う際は常に最新のセキュリティベストプラクティスに従ってください。

---

必要であれば README にサンプル .env.example、より詳細なコマンドライン実行例、CI 設定、ユニットテストの書き方などを追加します。追加希望があれば教えてください。