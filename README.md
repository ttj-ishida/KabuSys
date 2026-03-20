# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をデータ永続化層として利用し、J‑Quants API／RSS ニュース等からデータを取り込み、特徴量計算・シグナル生成・発注に繋がる一連の処理をモジュール化しています。

バージョン: 0.1.0

---

## 概要

KabuSys は次のレイヤーを持つシステム設計を前提とした Python パッケージです。

- Data (取得・ETL・品質検査・カレンダー管理・ニュース収集)
- Research (ファクター計算・探索分析)
- Strategy (特徴量正規化・シグナル生成)
- Execution (発注・ポジション・監査テーブル定義等)

設計上の特徴：
- DuckDB を用いたローカル DB（:memory: も可）
- J‑Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去）
- ルックアヘッドバイアス対策（フェッチ時刻や date を厳密に扱う）
- 冪等性を考慮した DB 保存（ON CONFLICT 等）

---

## 主な機能一覧

- データ取得 / 保存
  - J‑Quants から日足・財務・マーケットカレンダーを取得（jquants_client）
  - RSS ニュース収集・前処理・銘柄紐付け（news_collector）
  - DuckDB スキーマ定義 / 初期化（data.schema.init_schema）
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得（最終取得日から差分、バックフィル処理）
- 研究用ファクター計算（research.factor_research）
  - Momentum / Volatility / Value 等の計算
  - 将来リターン計算 / IC 計算 / 統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターのマージ、ユニバースフィルタ、Zスコア正規化、features テーブルへの保存
- シグナル生成（strategy.signal_generator）
  - ファクター・AIスコア統合 → final_score 計算 → BUY/SELL シグナル生成（signals テーブルへ保存）
- カレンダー管理（data.calendar_management）
  - 営業日判定・前後営業日の取得等のユーティリティ
- 監査 / 発注関連スキーマ（data.audit / schema）
  - signal_events / order_requests / executions などの監査ログテーブル

---

## 前提・インストール

必須:
- Python 3.10+（typing の | や型表記が使用されています）
- pip

推奨 Python パッケージ（最低限）:
- duckdb
- defusedxml

例（仮想環境内）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` に記載して読み込まれます（自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に利用される環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL (任意) — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

例 `.env`（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意: Settings で必須キーを参照すると未設定時に ValueError が発生します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン／取得
2. Python と依存ライブラリをインストール（上記参照）
3. `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

例:
```python
# init_db.py
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # デフォルトは data/kabusys.duckdb
conn = init_schema(db_path)
print("Initialized DB at", db_path)
```

コマンド実行:
```bash
python init_db.py
```

---

## 使い方（よく使う操作）

- DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J‑Quants トークンは settings を利用）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

- 特徴量の構築（features テーブル作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 15))
print("features upserted:", count)
```

- シグナル生成（signals テーブル作成）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2025, 1, 15))
print("signals written:", n)
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

エラーや詳細ログを出したい場合は logging の設定を行ってください。

---

## ディレクトリ構成

以下は主要なファイル/モジュールの一覧（src 側）：

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J‑Quants API クライアント（fetch/save）
    - news_collector.py             — RSS 取得 / 前処理 / 保存
    - schema.py                     — DuckDB スキーマ定義と初期化
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — マーケットカレンダー用ユーティリティ
    - features.py                   — features をエクスポート
    - audit.py                      — 監査ログスキーマ
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Volatility/Value の計算
    - feature_exploration.py        — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features 作成（正規化・フィルタ）
    - signal_generator.py           — final_score 計算とシグナル生成
  - execution/                       — 発注・実行周り（パッケージ構成はここに）
  - monitoring/                      — 監視関連（監視DBへの保存等）

（README 生成時点の主要モジュールを抜粋しています。実装ファイルはさらに細分されます）

---

## 注意事項 / トラブルシューティング

- Python バージョンは 3.10 以上を推奨します（構文に | 型が使用されています）。
- settings の必須環境変数が未設定だと ValueError が発生します。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用するか、環境変数を適切にセットしてください。
- J‑Quants API のレート制御は組み込まれていますが、API 利用制限やトークン期限に注意してください（get_id_token がリフレッシュを行います）。
- DuckDB のバージョン差異により FOREIGN KEY や ON DELETE 挙動が異なる場合があります（コード中に注意書きあり）。
- RSS 取得では SSRF 防止や最大受信サイズチェックを実施しています。特定フィードで受信に失敗する場合はログを確認してください。

---

## 貢献 / 開発メモ

- テストを行う際は自動で .env をロードする仕組みが働くため、意図せず環境変数が読み込まれるのを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- schema.init_schema は冪等で、既存テーブルは上書きしません。スキーマ変更時はマイグレーションを検討してください。
- 各モジュールは可能な限り外部 API への副作用を持たない設計（研究モジュール等）になっています。ユニットテスト時は外部呼び出しをモックしてください。

---

必要があれば、README に以下を追加できます：
- 具体的な requirements.txt / poetry / pyproject.toml の例
- CI 用の DB 初期化スクリプト（Docker Compose 等）
- 詳細な API 使用例（J‑Quants のパラメータ例）
- テーブルスキーマの ER 図や DataModel.md の抜粋

どの追加情報が必要か教えてください。