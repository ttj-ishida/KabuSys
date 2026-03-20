# KabuSys

日本株の自動売買プラットフォーム用ライブラリ（プロトタイプ）です。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査・Execution向けスキーマなどを内包します。

---

## 主要な目的（概要）

- J-Quants API から市場データ・財務データ・市場カレンダーを取得して DuckDB に保存する ETL パイプライン
- 研究用に計算された生ファクターを正規化・合成して戦略特徴量（features）を作成する機能
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成する機能（BUY/SELL）
- RSS などからニュースを収集し、記事と銘柄コードを紐付けるニュース収集機能
- DuckDB に対するスキーマ定義（冪等なテーブル定義／インデックス）、監査ログ用テーブル
- 安全性（SSRF対策、XMLパース保護）、API レート制限とリトライ制御などの実装

---

## 機能一覧

- data/
  - jquants_client: J-Quants API とやり取りするクライアント（レート制限、リトライ、トークンリフレッシュ対応）
  - pipeline: 差分取得ベースの日次 ETL（prices / financials / calendar）および品質チェック
  - schema: DuckDB のスキーマ初期化（init_schema）
  - news_collector: RSS 取得・前処理・DB 保存（SSRF/サイズ制限/トラッキングパラメータ除去）
  - calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティ
  - stats: Zスコア正規化などの汎用統計ユーティリティ
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ等
- strategy/
  - feature_engineering.build_features: 生ファクターのマージ、ユニバースフィルタ、Zスコア正規化、features テーブルへの UPSERT
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成・signals テーブル保存
- config:
  - 環境変数読み込み／検証（.env 自動ロード、必須チェック、環境別フラグ）
- execution / monitoring:
  - 実行層・監視層向けの骨組み（スキーマ等を提供）

主な設計方針：ルックアヘッドバイアス回避、冪等性（ON CONFLICT / トランザクション）、外部依存を最小化（研究コードは発注APIに依存しない）など。

---

## 前提（Prerequisites）

- Python 3.10+
- duckdb
- defusedxml

必要ライブラリはプロジェクトの packaging / requirements により異なります。最低限手動で入れるなら:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# その他必要なライブラリがあればインストールしてください
```

（パッケージ配布がある場合は `pip install -e .` 等でインストールできます）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトします。

2. 仮想環境を作成して依存をインストールします（例は上記参照）。

3. 環境変数を設定します。プロジェクトルートに `.env`（および `.env.local`）を置くと自動でロードされます（優先順: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（config.Settings 参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）

オプション / デフォルト:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: 監視用 sqlite のパス。デフォルト "data/monitoring.db"

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## データベース初期化

DuckDB スキーマを初期化するには `kabusys.data.schema.init_schema` を使用します。Python REPL やスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
# 以後 conn を使って ETL / feature / signal を実行できます
```

初回は親ディレクトリ（`data/`）を自動的に作成します。

---

## クイックスタート / 使い方例

1) 日次 ETL（J-Quants からデータを差分取得して保存）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量を構築（features テーブルへ書き込み）

```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成（features + ai_scores → signals テーブル）

```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

4) ニュース収集（RSS）と銘柄紐付け

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes は抽出に使用する銘柄コードセット（例: 全上場銘柄コード）
known_codes = {"7203", "6758", "9984", ...}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

注意: fetch_rss は外部 HTTP を行うためネットワーク例外に注意してください。news_collector は SSRF/サイズ上限/XML攻撃対策を組み込んでいます。

---

## 実装上の注記 / 動作仕様（重要ポイント）

- 環境変数は .env / .env.local を自動ロード（プロジェクトルートを .git または pyproject.toml を基準に探索）します。自動ロードをテスト等で無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントは 120 req/min のレート制限を守るようスロットリングし、408/429/5xx 等へのリトライ（指数バックオフ）と 401 の場合のトークン自動リフレッシュを行います。
- DB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本とし、トランザクションで日付単位置換を行って原子性を保ちます。
- 研究 / factor 計算モジュールは発注 API にアクセスせず、prices_daily / raw_financials のみを参照するため安全にオフライン解析できます。
- news_collector は URL 正規化（utm 等のトラッキング削除）により記事 ID を生成し、重複挿入を防ぎます。SSRF 対策と受信サイズ制限を実装しています。
- strategy の設計はルックアヘッドバイアス防止（対象日までのデータのみ使用）を徹底しています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル / ディレクトリは下記のような構成です（src/kabusys 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - stats.py
      - calendar_management.py
      - features.py
      - audit.py
      - audit のインデックス等...
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
    - monitoring/  (監視・運用用コードのスケルトン)
    - その他モジュール...

（README に掲載したのは主要モジュールと機能の抜粋です）

---

## テスト・開発時のヒント

- 自動環境ロードを無効化してユニットテストを行う場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のテスト用には ":memory:" を使うと速く初期化できます:
  - conn = init_schema(":memory:")
- ネットワークを伴うテスト（jquants_client / news_collector）は外部呼び出しをモックして実行することを推奨します（token キャッシュ / rate limiter を考慮）。

---

## ライセンス / コントリビューション

（ここにライセンスやコントリビューションルールを記載してください。プロジェクト固有のポリシーがあれば追記してください。）

---

README の内容は実装に基づく概要と使い方のガイドです。詳細な API 仕様や戦略モデルの数式（StrategyModel.md 等）は別ドキュメントとして管理してください。必要であれば README に追加したい実行例や運用手順を追記します。