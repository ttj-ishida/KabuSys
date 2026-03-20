# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行レイヤー等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ・財務データ・カレンダー取得（Rate limiting / retry / token refresh 対応）
- DuckDB ベースのデータスキーマ定義と冪等的な保存（Raw / Processed / Feature / Execution 層）
- ファクター計算（Momentum / Volatility / Value 等）と Z スコア正規化
- 特徴量（features）の構築と戦略に基づくシグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け
- ETL パイプライン / カレンダー管理 / 監査ログの補助関数群

設計上の特徴：
- ルックアヘッドバイアスを避けるため、target_date 時点のデータのみを参照
- DuckDB を用いた軽量かつ高速なローカルデータベース
- 冪等性を重視（ON CONFLICT / トランザクションで置換）
- 本番の発注処理（execution 層）への直接依存を持たない層設計

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・自動トークン更新・保存ユーティリティ）
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - pipeline: 日次 ETL 実行（run_daily_etl）・個別 ETL ジョブ
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出
  - calendar_management: JPX カレンダー管理・営業日判定
  - stats: 共通の統計ユーティリティ（zscore_normalize）
- research/
  - factor_research: Momentum / Volatility / Value の計算
  - feature_exploration: 将来リターン / IC / 統計サマリー等の解析ユーティリティ
- strategy/
  - feature_engineering: raw ファクターを統合・正規化して features テーブルへ保存（build_features）
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成（generate_signals）
- config: 環境変数の自動ロード（.env / .env.local）と Settings API
- audit / execution / monitoring: 監査ログ・実行関連（テーブル設計等）

---

## 必要条件 / 依存関係

- Python 3.10+
  - 理由: 型ヒントで `X | None` 等の構文を使用
- 主要ライブラリ（最小限）:
  - duckdb
  - defusedxml
  - （標準ライブラリで多くを実装していますが、実行環境に応じて追加パッケージが必要になる場合があります）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発パッケージとしてインストールする場合
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数

KabuSys は .env / .env.local をプロジェクトルートから自動読み込みします（既存 OS 環境変数優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（動作に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境作成・有効化
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 必要パッケージをインストール
```bash
pip install --upgrade pip
pip install duckdb defusedxml
# またはプロジェクトの依存に従ってインストール
pip install -e .
```

4. 環境変数を設定（.env をプロジェクトルートに作成）
5. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

---

## 使い方（簡単な流れ・サンプルコード）

基本的なワークフローの例：DB 初期化 → 日次 ETL 実行 → 特徴量構築 → シグナル生成

1. DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL 実行（J-Quants からデータ取得して保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量構築（strategy.feature_engineering.build_features）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4. シグナル生成（strategy.signal_generator.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals

num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {num_signals}")
```

5. ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効銘柄コードセット（例: DB から取得）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6. J-Quants の生データ取得 / 保存（必要に応じて）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved raw prices: {saved}")
```

---

## API のポイント（設計メモ）

- build_features / generate_signals は DuckDB 接続と target_date を受け取り、日付単位で既存レコードを削除して再挿入するため冪等（idempotent）です。
- jquants_client は内部で固定間隔のレート制御と再試行ロジック、401 時のトークンリフレッシュを実装しています。
- news_collector は SSRF・XML攻撃・GZip爆弾などの対策を組み込んでいます（defusedxml、レスポンスサイズ制限、プライベートアドレスチェック等）。
- calendar_management は market_calendar がなくても曜日ベースのフォールバックを行い、next/prev/get_trading_days が一貫した結果を返すように設計されています。

---

## ディレクトリ構成（抜粋）

以下は主なソースツリー（src 配下）です：

- src/kabusys/
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
    - audit/ (監査関連のDDLなど — 一部)
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
  - monitoring/ (監視関連モジュール想定)
  - その他 README 等

（実際のリポジトリには上記以外の補助ファイルやドキュメントが含まれる可能性があります）

---

## よくある運用ヒント

- 開発環境では KABUSYS_ENV=development、実運用では live を使用して挙動を切り替えます（設定に応じた安全チェックを行う想定）。
- 自動 .env 読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト時に明示的に環境を用意してください。
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb。複数環境で使う際は別ファイルを指定してください（:memory: でインメモリ DB も可）。
- ETL はネットワークや API の一時障害を許容するように設計されていますが、品質チェック（quality モジュール）による通知は運用側で確認してください。

---

## 開発に関する注意

- 本リポジトリのコードは API キーや実口座での発注ロジックに依存しない層で分割されていますが、本番運用時は入念なテストと安全策（発注前のドライラン、リスク制限、モニタリング）を実施してください。
- DuckDB の外部キーや ON DELETE 動作はバージョン差分の影響を受けるため、マイグレーションや削除処理はアプリ側で慎重に扱ってください（コメントにも注意事項あり）。

---

もし README に追加してほしい内容（例: 詳細な .env.example、デプロイ手順、CI 設定、サンプル SQL クエリ、よくあるエラー対処法など）があれば知らせてください。必要に応じて追記します。