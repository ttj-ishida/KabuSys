# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL・データ品質チェック、特徴量生成、監査ログ、ニュース収集などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン更新対応）
- DuckDB を用いたデータスキーマ定義と冪等的な永続化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ

設計上、実際の発注 API（kabuステーション等）や本番口座へのアクセスは別モジュール（execution 等）と分離されており、data / research モジュールは本番の発注ロジックに影響を与えません。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（rate limiter、リトライ、トークン自動リフレッシュ）
  - fetch / save の冪等処理（DuckDB へ ON CONFLICT を用いた保存）
- data/schema.py
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化
- data/pipeline.py
  - 日次 ETL（差分取得、バックフィル、品質チェック）Run: run_daily_etl
- data/news_collector.py
  - RSS フィード取得、前処理、記事保存、銘柄抽出（SSRF対策・gzip制限・XML安全パース）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- research/factor_research.py
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials のみ参照）
- research/feature_exploration.py
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、ランク化ユーティリティ
- data/audit.py
  - 監査ログ（signal_events, order_requests, executions）スキーマ/初期化

その他、設定管理（kabusys.config）や統計ユーティリティ（data.stats）を含みます。

---

## 動作環境 / 依存

- Python 3.10 以上（注: 型ヒントに | 演算子を使用）
- 主要な依存パッケージ
  - duckdb
  - defusedxml

（標準ライブラリの urllib 等を多用しており必須依存は少なめです。プロジェクトに合わせて追加の依存が必要になる場合があります。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   (プロジェクト配布に requirements.txt がある場合はそちらを使用)
   ```
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 開発時に編集したい場合:
   pip install -e .
   ```

4. 環境変数／.env の準備
   settings で参照される環境変数を設定してください（.env をプロジェクトルートに置くと自動ロードされます）。
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - KABU_API_PASSWORD: kabu API パスワード（発注モジュール使用時）
   - 任意（デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|...
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
   自動ロードを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（サンプル）

以下は最小限の利用例です。DuckDB スキーマを初期化して日次 ETL を実行します。

1) DB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ディレクトリが無ければ自動作成
```

2) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ本日を対象
print(result.to_dict())
```

3) ニュース収集ジョブ（既知銘柄セットを渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"6758", "7203", "9432"}  # 例: 有効銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) 研究用ファクター計算の使用例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# その後 zscore_normalize 等で正規化可能
```

注意点:
- J-Quants API を叩く処理は認証トークン（JQUANTS_REFRESH_TOKEN）が必要です。
- ETL を実行する際に network エラーや API 制限などが発生する可能性があるためログを確認してください。

---

## 環境変数一覧（代表）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack) — Slack 通知トークン
- SLACK_CHANNEL_ID (必須 for Slack) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 開発環境フラグ（development|paper_trading|live）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py      — RSS 収集・前処理・DB保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize など統計ユーティリティ
    - calendar_management.py — 市場カレンダー関連ユーティリティ
    - audit.py               — 監査ログスキーマ / 初期化
    - features.py            — feature ユーティリティ（再エクスポート）
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - strategy/                 — 戦略層（空の __init__、実装は別途）
  - execution/                — 発注/ブローカー連携層（空の __init__、実装は別途）
  - monitoring/               — 監視・メトリクス（未実装箇所あり）

---

## 開発者向けノート

- 型注釈や union 型（|）を多用しているため Python 3.10 以上を推奨します。
- DuckDB への接続は data.schema.init_schema()（初期化）または get_connection()（既存 DB）を利用してください。
- テストや CI で自動的に .env を読み込みたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- news_collector は外部ネットワークに依存するため、単体テスト時は _urlopen やネットワーク呼び出しをモックしてください。

---

## ライセンス・貢献

（ここにライセンス情報や貢献ルール、Issue / PR の出し方を記載してください）

---

必要であれば、README に次の内容を追加できます:
- より詳細な環境変数サンプル（.env.example）
- 典型的なデプロイ手順 / cron ジョブ例（ETL の定期実行）
- 発注（execution）モジュールの利用例（kabu API 連携）
- CI / テストの実行方法

どれを追加しますか？