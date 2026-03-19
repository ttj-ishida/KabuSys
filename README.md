# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
Market データ取得（J-Quants）、ETL、DuckDB ベースのスキーマ、特徴量算出、シグナル生成、ニュース収集、監査ログなど一連の機能を提供します。パッケージは src/kabusys 以下のモジュール群で構成されています。

## 主な目的
- J-Quants API からのデータ取得と差分 ETL
- DuckDB による Raw / Processed / Feature / Execution 層のデータ管理
- 研究用ファクター計算・特徴量正規化
- 戦略用シグナル生成（BUY/SELL 判定）
- ニュース RSS の収集と銘柄紐付け
- 発注監査ログ（トレーサビリティ）設計のためのスキーマ

---

## 機能一覧
- データ取得
  - J-Quants から株価日足、財務データ、マーケットカレンダーをページネーション対応で取得（認証・自動リフレッシュ・レート制御・リトライ）
- ETL / Data Pipeline
  - 差分取得（最終取得日からの差分）、バックフィル対応、品質チェックフック
  - 市場カレンダー先読み（lookahead）対応
- データベース
  - DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, orders, trades, positions, audit テーブル等）の初期化 / 接続ユーティリティ
- 特徴量 / 研究
  - momentum / volatility / value 等のファクター計算（research モジュール）
  - Z スコア正規化ユーティリティ
  - 将来リターン（forward returns）・IC（Information Coefficient）計算・統計サマリー
- シグナル生成
  - 正規化済み特徴量と AI スコアの統合による final_score 計算
  - Bear レジーム抑制、BUY/SELL 判定、冪等な signals テーブル書き込み
- ニュース収集
  - RSS 取得（SSRF対策・Gzip制限・XML防御）、記事IDの冪等保存、本文前処理、銘柄抽出（4桁コード）
- カレンダー管理
  - 営業日判定・next/prev trading day ユーティリティ、夜間カレンダー更新ジョブ
- 監査（Audit）
  - シグナル→発注→約定までのトレース用テーブル設計（監査ログ用 DDL）

---

## 要求 / 依存パッケージ（例）
- Python 3.9+
- duckdb
- defusedxml

（プロジェクトの packaging / pyproject.toml に依存関係が定義されているはずです。ローカルで使う場合は下記のように最低限を用意してください。）

例:
pip install duckdb defusedxml

また開発インストール:
python -m pip install -e .

---

## 環境変数（主要）
プロジェクトは環境変数または .env/.env.local ファイルから設定を読み込みます（優先順: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...) デフォルト "INFO"
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（"1"）

設定は kabusys.config.settings オブジェクト経由で参照できます。

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境を作成・有効化（推奨）
3. 必要パッケージをインストール
   - python -m pip install -e .  または  pip install duckdb defusedxml
4. .env を作成して必須変数を設定（例は .env.example を参照）
5. DuckDB スキーマ初期化
   - Python から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

例（コマンドライン）:
```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

---

## 使い方（代表的な操作例）

1) DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリ自動作成
```

2) 日次 ETL 実行（市場カレンダー取得・株価・財務データの差分取得・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 1))
print(f"upserted features: {n}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n_signals = generate_signals(conn, target_date=date(2025,3,1))
print(f"signals written: {n_signals}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事から銘柄紐付けを行う
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # source_name => 新規保存数
```

6) J-Quants API 直接利用例（トークン自動取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
recs = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
print(len(recs))
```

注意: 実行時は環境変数（特に JQUANTS_REFRESH_TOKEN）が必要です。

---

## 自動 .env ロードの振る舞い
- 実行時にパッケージはプロジェクトルート（.git または pyproject.toml のある場所）を探し、そこにある `.env` と `.env.local` を自動で読み込みます。
- 読み込み順:
  1. OS 環境変数（最優先）
  2. .env（未設定キーのみセット）
  3. .env.local（存在すれば上書き。ただし OS 環境変数は保護）
- 自動ロード無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

.env のパース挙動:
- export KEY=val 形式を許容
- シングル/ダブルクォート内のエスケープを処理
- コメント(#) 取り扱いに細かなルールあり（空白直前の#はコメントとみなす）

---

## ディレクトリ構成（主要ファイル / モジュール）
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py                  — DuckDB スキーマ定義・初期化
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - stats.py                   — Zスコア等の統計ユーティリティ
    - news_collector.py          — RSS 収集・保存・銘柄抽出
    - calendar_management.py     — カレンダー管理 / 更新ジョブ / 営業日ユーティリティ
    - features.py                — 公開特徴量ユーティリティ（ラッパー）
    - audit.py                   — 監査ログ用 DDL と初期化
    - ...（quality 等 他モジュール想定）
  - research/
    - __init__.py
    - factor_research.py         — momentum/volatility/value 等ファクター計算
    - feature_exploration.py     — IC, forward returns, summary
  - strategy/
    - __init__.py
    - feature_engineering.py     — ファクター統合・Zスコア正規化 → features テーブルへ
    - signal_generator.py        — final_score 計算と signals テーブル書き込み
  - execution/                   — 発注/実行レイヤ（パッケージ用意）
  - monitoring/                  — 監視・メトリクス収集用（パッケージ用意）

---

## 設計上の注意点 / ベストプラクティス
- データ取得・ETL・シグナル生成はすべて「ルックアヘッドバイアス」を避けるように設計されています。各処理は target_date 時点で利用可能なデータのみを参照します。
- DB への書き込みは可能な限り冪等（ON CONFLICT / UPSERT）で実装されています。
- J-Quants の API リトライ/レート制御はモジュール内で行われますが、APIキー・トークンは安全に管理してください。
- 本番運用（live）時は KABUSYS_ENV を "live" に設定し、paper_trading との切替・ログレベル等を適切に管理してください。
- news_collector は SSRF 対策や XML Bomb 対策（defusedxml）を組み込んでいますが、外部ソースの安全性には常に注意してください。

---

もし README に追加したいサンプルスクリプト、CI、テスト手順や .env.example のテンプレートが必要であれば教えてください。