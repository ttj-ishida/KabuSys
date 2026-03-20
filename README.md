# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
DuckDB をデータストアに用い、J-Quants からの市場データ収集、品質チェック、特徴量生成、シグナル生成、ニュース収集、監査ログまでをカバーするモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを実装したモジュール群を含みます。

- Data layer: J-Quants API クライアント、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプライン、品質チェックなど
- Research layer: ファクター計算（モメンタム、ボラティリティ、バリュー）・特徴量探索ユーティリティ
- Strategy layer: 特徴量の正規化・合成（features 作成）と最終スコア計算によるシグナル生成
- Execution / Audit layer: テーブル設計（orders/trades/positions 等）と監査ログのためのスキーマ（実際の broker 実装は含まず）

設計上の特徴:
- DuckDB を単一の永続 DB として使用（ファイルまたは :memory:）
- 取得・保存は冪等（ON CONFLICT）で安全に実行
- ルックアヘッドバイアス対策（計算は target_date 時点のデータのみ参照）
- ニュース収集は SSRF 対策や XML 攻撃対策を実施
- J-Quants API へのリクエストはレート制限・リトライ・トークン自動リフレッシュ対応

---

## 主な機能一覧

- J-Quants API クライアント（fetch / save 処理、ページネーション、トークン管理、レート制御）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層のテーブル）
- ETL パイプライン（市場カレンダー・株価・財務の差分取得、バックフィル、品質チェック含む）
- ファクター計算（momentum / volatility / value）および Z スコア正規化ユーティリティ
- 特徴量生成（build_features: ファクター合成・フィルタリング・正規化・features テーブル保存）
- シグナル生成（generate_signals: final_score 計算、BUY/SELL 判定、signals テーブル保存）
- RSS ベースのニュース収集（fetch_rss / save_raw_news / extract_stock_codes / run_news_collection）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
- 監査ログスキーマ（signal_events / order_requests / executions 等）

---

## 必要環境

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外が増えた場合は requirements に追加してください）

例:
```
python -m pip install "duckdb" "defusedxml"
```

パッケージとして開発インストールする場合:
```
pip install -e .
```
（プロジェクトに setup / pyproject がある前提です）

---

## 環境変数 / .env

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（実運用で実行する場合）
- SLACK_BOT_TOKEN: Slack 通知（必要なら）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必要なら）

任意（既定値あり）:
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境を指定（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 環境を作成（推奨: venv）
3. 必要パッケージをインストール
4. 環境変数を設定（.env をプロジェクトルートに配置）
5. DuckDB スキーマを初期化

コマンド例:
```bash
git clone <repo-url>
cd <repo-dir>

python -m venv .venv
source .venv/bin/activate

pip install -e .     # または必要パッケージを個別にインストール
# pip install duckdb defusedxml

# プロジェクトルートに .env を作成して必要な環境変数を設定

python - <<'PY'
from pathlib import Path
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

db_path = settings.duckdb_path  # 環境変数から取得（ない場合は data/kabusys.duckdb）
conn = init_schema(db_path)
print("DuckDB initialized:", db_path)
conn.close()
PY
```

---

## 使い方（よく使う操作例）

以下は典型的なワークフローの抜粋です。実運用ではジョブスケジューラ（cron / systemd timer / Airflow 等）から呼び出します。

1) DuckDB スキーマ初期化（上記参照）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー・価格・財務の差分取得）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())  # ETLResult が返る
print(result.to_dict())
conn.close()
```

3) 特徴量をビルド（build_features）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナルを生成（generate_signals）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.60)
print("signals written:", count)
```

5) ニュース収集ジョブ
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203","6758", ...}  # データベースや別ソースから取得した有効銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar rows saved:", saved)
```

ログ出力や監視は環境のログ設定に従ってください（settings.log_level を参照）。

---

## 注意点 / 設計上の留意事項

- 計算関数（feature, signal 等）は target_date の時点のみのデータを参照し、ルックアヘッドバイアスを避けるよう設計されています。
- J-Quants API の呼び出しはレート制限（120 req/min）を守るため固定スロットリングとリトライを実装していますが、本番で大量取得する場合は注意してください。
- DuckDB のトランザクションは多用します。大規模一括挿入時はチャンク分割やトランザクション境界に気をつけてください。
- ニュース収集は外部 URL の検証（スキーム検査、プライベート IP ブロック）や XML の安全パース（defusedxml）を実施しています。それでも社内ネットワークポリシーに合わせた運用を推奨します。
- 環境変数を .env に置く際は秘匿情報の管理に注意してください（VCS にコミットしない等）。

---

## ディレクトリ構成

以下は主要なソースファイルとモジュール構成の抜粋です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                           # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py                 # RSS ニュース収集・保存
    - schema.py                         # DuckDB スキーマ定義・初期化
    - stats.py                          # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - features.py                       # zscore_normalize の再エクスポート
    - calendar_management.py            # カレンダー管理（営業日判定 等）
    - audit.py                          # 監査ログ・DDL（signal_events, order_requests 等）
  - research/
    - __init__.py
    - factor_research.py                # モメンタム/ボラティリティ/バリュー算出
    - feature_exploration.py            # 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py            # build_features（正規化・フィルタ・UPSERT）
    - signal_generator.py               # generate_signals（final_score, BUY/SELL）
  - execution/                           # 発注/モニタリング関連（空のパッケージ / 拡張用）
  - monitoring/                          # 監視・外部連携用（今後の追加箇所）

（実際のリポジトリには README、pyproject.toml やテスト、CI 設定等も含まれる想定です）

---

## 今後の拡張候補

- broker 用の execution 層（kabu API 連携ラッパー）の具象実装
- AI スコア連携・学習パイプラインの追加
- 可視化・バックテストツール（戦略評価ダッシュボード）
- 高度なリスク管理モジュール（ポジションサイズ計算、ドローダウン制御等）

---

## サポート / 貢献

バグ報告や機能提案は Issue を作成してください。プルリクエストは歓迎します。コーディング規約やテストを追加することで品質向上に寄与できます。

---

README の内容や例は現在の実装（src/kabusys/*.py）に基づいてまとめています。運用前に必ずローカルで動作確認を行い、API トークン・パスワードなどの秘密情報は安全に管理してください。