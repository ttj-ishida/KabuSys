# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants API など外部データソースからのデータ取得、DuckDB を用いたデータ格納・スキーマ管理、特徴量計算・正規化、シグナル生成、RSS ニュース収集、マーケットカレンダー管理、ETL パイプライン等を提供します。

主に研究→本番のワークフロー（research → data → strategy → execution）を想定した設計で、ルックアヘッドバイアス防止・冪等性・堅牢なエラーハンドリングを重視しています。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数/設定管理（.env 自動読み込み、必須変数チェック）
- DuckDB スキーマの定義・初期化（raw / processed / feature / execution 各レイヤー）
- J-Quants API クライアント
  - 日次の株価（OHLCV）取得（ページネーション対応）
  - 財務データ取得（四半期 BS/PL）
  - JPX マーケットカレンダー取得
  - レート制限管理・リトライ・トークン自動リフレッシュ等を実装
- ETL パイプライン（差分取得・保存・品質チェック統合）
- 特徴量計算モジュール（モメンタム / バリュー / ボラティリティ 等）
- 特徴量正規化（Zスコア正規化）
- シグナル生成（特徴量 + AI スコア融合 → BUY / SELL シグナル生成、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS 取得、テキスト前処理、銘柄抽出、DB 保存、SSRF / XML 攻撃対策）
- マーケットカレンダー管理（営業日判定、次/前営業日検索、夜間更新ジョブ）
- 監査（audit）スキーマ群（シグナル→発注→約定 を UUID で追跡）
- ユーティリティ（統計・ランキング・IC 計算 など）

---

## 必要環境 / 依存

- Python 3.10+
- 推奨パッケージ（代表例）:
  - duckdb
  - defusedxml
  - （その他: logging や標準ライブラリのみで実装されている箇所もあります）

（プロジェクト配布で requirements.txt があればそちらを使用してください）

---

## 環境変数（主なもの）

Settings クラスで参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（発注連携を行う場合）
- KABU_API_BASE_URL — kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 BOT トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルへのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development|paper_trading|live)、デフォルトは development
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン、作業ディレクトリへ移動。
2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール:
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば: pip install -r requirements.txt）
4. (任意) ローカル開発インストール:
   - pip install -e .

5. `.env` を作成して必要な環境変数を設定（.env.example を参考に作成してください）。

---

## 使い方（主要 API の例）

以下は Python スクリプト / REPL からの呼び出し例です。各操作は duckdb 接続（kabusys.data.schema.init_schema / get_connection）を使います。

- DuckDB スキーマ初期化（ファイルを作成してテーブルを作る）:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値またはデフォルト
conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行する（J-Quants から差分取得して保存）:

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量（features）を構築する（target_date の分）:

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2025, 1, 31))
print("upserted features:", count)
```

- シグナル生成（features / ai_scores を参照して signals を生成）:

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, date(2025, 1, 31))
print("generated signals:", num_signals)
```

- RSS ニュース収集ジョブ（既知銘柄セットを渡して銘柄紐付け）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- マーケットカレンダー夜間更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意事項:
- 各関数は冪等性（同じデータの再投入で重複が起きない）を意識して実装されています（ON CONFLICT など）。
- ETL / API 呼び出しはネットワークや API レート制限の影響を受けます。ログを確認してください。
- 実運用時は KABUSYS_ENV を適切に設定（paper_trading や live）し、発注系のテストはペーパートレードで十分に検証してください。

---

## ディレクトリ構成（主要ファイルと説明）

（パッケージルートでは src/kabusys 配下に実装があります）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス（必須変数チェック）
  - data/
    - __init__.py
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py
      - J-Quants API クライアント（レート制御、リトライ、保存ユーティリティ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - news_collector.py
      - RSS 取得・前処理・DB 保存・銘柄抽出
    - calendar_management.py
      - カレンダー更新・営業日判定ユーティリティ
    - features.py
      - zscore_normalize のエクスポート（data.stats を再公開）
    - stats.py
      - zscore_normalize など統計ユーティリティ
    - audit.py
      - 監査ログ用の DDL（signal_events / order_requests / executions 等）
    - (その他) quality.py（品質チェックは pipeline から呼ばれる想定）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム／バリュー／ボラティリティ等の計算（prices_daily / raw_financials を参照）
    - feature_exploration.py
      - forward returns, IC（Spearman）計算, summary utilities
  - strategy/
    - __init__.py
    - feature_engineering.py
      - raw ファクターを合成して features テーブルへ保存（Z スコア正規化等）
    - signal_generator.py
      - features と ai_scores を統合して final_score を計算、BUY/SELL を signals テーブルへ保存
  - execution/
    - __init__.py
    - （発注・ブローカー連携はこの層で実装される想定）
  - monitoring/
    - （監視 / メトリクス関連の実装を想定）

README に書かれている以外にも、テスト用フックや補助ユーティリティが各モジュールにあります。各モジュールの docstring に利用方法や設計意図が記載されていますので、実装を読むと詳細が分かります。

---

## 運用上の注意

- 本ライブラリは発注ロジック（execution 層）と研究（research 層）を分離しています。発注を有効にする前に必ずペーパートレード環境での検証を行ってください。
- 環境変数に機密情報（API トークン等）を保存する際は管理に注意してください。
- DuckDB ファイルはバックアップを取ることを推奨します（データの永続性確保）。
- J-Quants の API レート制限（120 req/min）などを尊重すること。jquants_client はレート制御を行いますが、過負荷をかけない運用が重要です。

---

必要であれば、README にサンプル .env.example、運用手順（cron / Airflow などでの定期実行例）、さらに詳細な API ドキュメント（各関数の引数・返り値の説明）を追記できます。どの情報を追加したいか教えてください。