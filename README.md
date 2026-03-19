# KabuSys

日本株向けの自動売買（データプラットフォーム＋戦略）ライブラリです。  
DuckDB をデータ層に用い、J-Quants API から市場データ・財務データ・カレンダーを取得して ETL → 特徴量作成 → シグナル生成までをサポートします。設計はルックアヘッドバイアス回避・冪等性・堅牢なエラーハンドリングを重視しています。

バージョン: 0.1.0

---

## 概要

- データ取得（J-Quants）→ 生データ保存（raw layer）→ 整形（processed layer）→ 特徴量（feature layer）→ 戦略シグナル（execution layer）という 3 層＋実行層のアーキテクチャを提供します。
- DuckDB を用いたオンディスク DB（またはインメモリ）を前提に設計されています。
- ニュース収集（RSS）・AI スコア統合・ポートフォリオ整備・発注監査ログまで想定したテーブル定義が含まれます。
- ルックアヘッドバイアス防止（取得時刻の記録など）、API レート制御、リトライ、SSRF 対策など運用を意識した実装が含まれます。

---

## 主な機能

- データ取得
  - J-Quants API クライアント（株価日足 / 財務データ / マーケットカレンダー）
  - 固定間隔のレートリミット、リトライ、トークン自動リフレッシュ対応
- データ保存
  - DuckDB スキーマ定義（raw / processed / feature / execution）
  - 冪等保存（ON CONFLICT / INSERT ... RETURNING を活用）
- ETL パイプライン
  - 差分取得（最終取得日からの差分 + バックフィル）
  - カレンダーの先読み、品質チェックフロー（品質チェックモジュール呼び出し）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリー
- 特徴量・戦略
  - 特徴量作成（Zスコア正規化、ユニバースフィルタ）
  - シグナル生成（複数コンポーネントスコアの重み付け、Bear レジーム抑制、エグジット判定）
- ニュース収集
  - RSS 取得、URL 正規化、記事ID (SHA-256) 生成、記事保存、銘柄抽出・紐付け
  - XML/SSRF 対策、サイズ上限、gzip 解凍検査
- 監査（Audit）
  - signal → order_request → executions まで追跡できる監査用テーブル群

---

## 必要条件

- Python 3.10+
  - 型注釈に `X | Y`（PEP 604）や型ユニオンを使っているため Python 3.10 以降を想定しています。
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの実際の requirements.txt / pyproject.toml を参照してインストールしてください）

---

## 環境変数 / 設定

`kabusys.config.Settings` が環境変数を参照します。自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組みがあります（無効化可能: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用の Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack の通知先チャンネル ID（必須）

その他オプション / デフォルト:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- KABUSYS_* のほか DB パス等:
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"
  - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   または必要最小限:
   - pip install duckdb defusedxml
4. 環境変数を設定（.env を作成）
   - プロジェクトルートに `.env` を作成し必要なキーを設定
5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで以下を実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - これにより data ディレクトリが作られ、必要なテーブルがすべて作成されます

---

## 使い方（主要ワークフロー例）

以下はライブラリ API を直接呼ぶ簡単な例です。CLI は提供されていないため、スクリプトや Cron / Airflow 等から呼び出して運用します。

1. DB の初期化（1回）
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL 実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3. 特徴量構築（strategy の前段）
```
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {count}")
```

4. シグナル生成
```
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2025, 1, 15))
print(f"signals written: {n}")
```

5. ニュース収集（RSS）および銘柄抽出
```
from kabusys.data.news_collector import run_news_collection
# known_codes は抽出対象の有効銘柄コード集合
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

6. J-Quants からのデータ取得（低レベル）
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(code="7203", date_from=..., date_to=...)
```

ログレベルや動作モードは環境変数（KABUSYS_ENV, LOG_LEVEL）で制御します。`KABUSYS_ENV=live` に設定すると本番モード判定に影響します（発注フローのガード等）。

---

## ディレクトリ構成（主なファイル）

以下はソースルートが `src/kabusys/` の場合の主要構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存ロジック
    - news_collector.py      # RSS 取得・記事保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py # カレンダー管理ユーティリティ
    - audit.py               # 発注/約定の監査テーブル定義
    - features.py            # データ層向けユーティリティ再エクスポート
    - stats.py               # Zスコア等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Volatility / Value の計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py # features テーブル作成ロジック（正規化等）
    - signal_generator.py    # final_score 計算・BUY/SELL の生成
  - execution/                # 発注/ブローカー連携（空ディレクトリまたは未実装の箇所あり）
  - monitoring/               # 監視・メトリクス（実装に応じて追加）

---

## 運用上の注意点

- 環境変数管理:
  - 開発中は `.env.local` を使ってローカル上書きが可能（自動ロード順: OS env > .env.local > .env）。
  - テストや CI で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルの取り扱い:
  - DB ファイルを複数プロセスで同時に書き換える場合は整合性に注意してください（用途によっては専用の排他制御が必要）。
- API レート制限:
  - J-Quants のレート制限（120 req/min）に準拠する実装が含まれていますが、大量の並列処理を行う場合は全体設計を検討してください。
- セキュリティ:
  - news_collector には SSRF 対策・XML 脆弱性対策（defusedxml）を組み込んでいますが、外部 URL を扱う部品は運用ポリシーに従ってください。

---

## 貢献 / 拡張ポイント

- execution 層のブローカー API 実装（kabuステーション連携等）
- リアルタイム監視（監視系の具体実装）
- モデル・AI スコアの統合ワークフロー（外部スコアを取り込むバッチ）
- 品質チェックモジュール（quality）の充実（ETL pipeline が呼び出す想定）

---

もし README に追加したい「サンプルスクリプト」「CI 設定」「実運用のデプロイ手順」などがあれば、その目的に合わせて追記例を作成します。