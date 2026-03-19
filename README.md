# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリセット（研究／データプラットフォーム／戦略生成／ETL／監査用ユーティリティ）

このリポジトリは、J‑Quants 等の外部データソースから市場データを取得して DuckDB に蓄積し、特徴量（features）を生成、戦略スコアと AI スコアを統合して売買シグナルを作成する一連の処理をモジュール化した Python パッケージです。発注・実行（execution）層や監視（monitoring）層との連携を想定した設計になっています。

主な設計方針
- ルックアヘッドバイアスを排除する（target_date 時点のデータのみ参照）
- DuckDB を中心としたローカルデータプラットフォーム（冪等性を重視）
- J‑Quants API のレート制御・トークン自動リフレッシュ・リトライを実装
- ニュース収集は SSRF / XML Bomb / 大量データ対策を実装
- Strategy / Research / Data 層を分離しユニットテストしやすい構成

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local を自動ロード（必要に応じて無効化可）
  - 必須環境変数の取得とバリデーション（env, log level 等）
- Data 層
  - J‑Quants API クライアント（fetch / save / ページネーション / rate limit / retry / token refresh）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（日次 ETL：calendar / prices / financials の差分更新と品質チェック）
  - ニュース収集（RSS フィード取得、正規化、raw_news 保存、記事→銘柄紐付け）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - 統計ユーティリティ（Zスコア正規化など）
- Research 層
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- Strategy 層
  - 特徴量作成（feature_engineering.build_features）：research の生ファクターを正規化して features テーブルへ保存
  - シグナル生成（signal_generator.generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存
- Audit / Execution（スキーマ：監査ログ / orders / executions / positions 等）
- セキュリティ・堅牢性機能：入力検証、トランザクション + バルク挿入による原子性、各所でのログと例外ハンドリング

---

## セットアップ手順

前提：Python 3.9+（typing の一部記法を利用）を推奨します。

1. リポジトリをクローン / 取得
   - パッケージは `src/` 配下にあるため、プロジェクトルートからインストールします。

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 代表的な外部依存（少なくとも以下をインストールしてください）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 開発インストール（editable）
   - プロジェクトルートで:
     - pip install -e .

5. 環境変数設定
   - `.env` または環境変数で設定します。自動ロードはパッケージ読み込み時にプロジェクトルート (`.git` または `pyproject.toml`) を基準に行われます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（最低限設定が必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

   - .env の最小例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要なユースケース）

以下は Python スクリプトから各主要処理を呼び出す例です。

1. DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを指定、":memory:" でインメモリ
```

2. 日次 ETL（J‑Quants からデータ取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量作成（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4. シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

5. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")

# known_codes: 銘柄抽出に使用する有効なコードセット（省略可）
known_codes = {"7203", "6758", "9432"}
results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

6. カレンダー更新バッチ
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点
- run_daily_etl では内部で市場カレンダーを先に取得し、営業日に調整した上で株価・財務の差分 ETL を実行します。
- jquants_client は 120 req/min のレート制限を守るため内部でスロットリングを行い、401（トークン期限切れ）時は自動で ID トークンをリフレッシュして再試行します。
- ニュース収集は外部 URL の検証や受信サイズ制限、XML の安全なパースを実装しています。

---

## 設計上の注意・運用上のヒント

- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" の 3 種類のみ許容されます。実際の発注を行う場合は live と paper_trading を使い分けてください。
- DuckDB はファイルベースの組込み DB です。マルチプロセスでの書き込みを行う場合は運用上の注意が必要です（単一プロセスでの ETL / バッチを推奨）。
- features / signals 作成は幾つかのステップ（ETL → feature build → signal generation）を順に行うフローが一般的です。運用スケジュールとしては ETL → features → ai スコア反映 → signals の順で一日のバッチを構成してください。
- 実行時のログレベルは環境変数 LOG_LEVEL で制御できます。デバッグ時には DEBUG を設定してください。
- .env の自動ロードはパッケージ import 時に行われ、OS 環境変数が優先されます。テストや CI で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

以下はパッケージの主要ファイル構成（src/kabusys 配下）です。実際のリポジトリにはさらに補助ファイルやドキュメントが含まれる可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J‑Quants API クライアント（fetch/save）
      - news_collector.py      — RSS ニュース収集と保存
      - schema.py              — DuckDB スキーマ定義・初期化
      - stats.py               — 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py — カレンダー管理（is_trading_day 等）
      - features.py            — data 層の features 公開インターフェース
      - audit.py               — 監査ログ用 DDL（signal_events / order_requests 等）
    - research/
      - __init__.py
      - factor_research.py     — momentum/volatility/value 計算（research 層）
      - feature_exploration.py — IC/forward_returns/factor_summary
    - strategy/
      - __init__.py
      - feature_engineering.py — 生ファクターから features を作成
      - signal_generator.py    — features + ai_scores を統合して signals を生成
    - execution/                — 発注/約定管理（空ファイルあり、拡張想定）
    - monitoring/               — 監視関連（拡張想定）
    - その他モジュール...

---

## 貢献・拡張ポイント（例）

- execution 層の証券会社 API 実装（kabu API client など）
- リアルタイム実行やスケジューラ統合（Airflow / cron / Cloud Functions）
- ai_scores の自動生成パイプライン（NLP / 生成モデルを使ったニューススコア算出）
- 単体テスト・CI ワークフローの整備（mock による外部 API テスト）
- モニタリング・アラート（Slack 通知、Prometheus など）

---

## ライセンス・免責

- 本 README はソースコードに基づく概要説明です。実運用では API キーやトークンの管理、証券取引の法的要件を遵守してください。
- 実際の売買・資金管理に関しては自己責任で行ってください。本ライブラリは投資損失について一切責任を負いません。

---

必要であれば、README に実際の requirements.txt の候補、CI 用の例、または個別モジュール（signal_generator / feature_engineering / jquants_client）の詳細ドキュメントを追加できます。どの情報を優先して追記しますか？