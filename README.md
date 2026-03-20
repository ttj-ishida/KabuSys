# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に使い、J-Quants API や RSS を取り込み、研究（research）→ 特徴量生成（feature）→ シグナル生成（strategy）→ 発注/監視（execution / monitoring）までの典型的なワークフローを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存する ETL（差分取得・バックフィル対応）。
- RSS を収集してニュース記事を保存・銘柄紐付けするニュース収集機能。
- research モジュール群でファクター（モメンタム / ボラティリティ / バリュー 等）を計算。
- 特徴量正規化（Z スコア）と features テーブルの構築。
- features と AI スコアを統合して売買シグナル（BUY / SELL）を生成。
- DuckDB スキーマ定義・初期化、各種ユーティリティ（マーケットカレンダー操作、統計ユーティリティ等）。

設計方針の一部：
- ルックアヘッドバイアスを防ぐため、target_date 時点のデータのみを使用。
- DuckDB へは冪等な保存（ON CONFLICT DO UPDATE / DO NOTHING）を実施。
- 外部依存を最小化（pandas 等に依存しない実装を志向）。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（jquants_client）：日足、財務、マーケットカレンダーの取得・保存（ページネーション・レート制御・リトライ・トークン自動更新対応）
  - ETL パイプライン（data.pipeline）：差分取得、バックフィル、品質チェック、日次 ETL 集約
  - DuckDB スキーマ初期化（data.schema）：Raw / Processed / Feature / Execution レイヤーのテーブル群定義

- ニュース収集
  - RSS フェッチ・前処理・記事保存（data.news_collector）
  - 記事 ID の冪等生成（URL 正規化 + SHA-256）
  - 銘柄コード抽出・news_symbols 保存

- 研究・特徴量
  - ファクター計算（research.factor_research）：mom, volatility, value 等
  - 特徴量探索・IC 計算（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats / data.features）

- 戦略
  - 特徴量構築（strategy.feature_engineering: build_features）
  - シグナル生成（strategy.signal_generator: generate_signals）
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）を統合
    - Bear レジーム抑制、停止損失（stop-loss）や score 閾値判定による SELL 判定
    - signals テーブルへの日次置換（冪等）

- カレンダー / ユーティリティ
  - 営業日判定 / next/prev_trading_day / get_trading_days（data.calendar_management）
  - 監査ログ用 DDL（data.audit）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型表記などを使用）
- DuckDB を利用可能な環境

1. 仮想環境を作成・有効化（任意）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   - 最低限の依存:
     ```
     pip install duckdb defusedxml
     ```
   - 開発中はパッケージを編集可能インストール:
     ```
     pip install -e .
     ```
     （プロジェクトが PEP517/pyproject.toml 構成であれば pip install -e . が使えます）

   注意: requirements.txt / pyproject.toml は本リポジトリに合わせて利用してください。

3. 環境変数設定
   - .env または OS 環境変数で設定できます。自動ロードはプロジェクトルートの .env/.env.local を検出して行われます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 必須環境変数（settings で _require されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live)（default: development）
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)（default: INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（基本例）

以下はパッケージ利用の代表的なワークフロー例です。実行は Python スクリプト / ジョブとして組み込んでください。

1. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb にファイルを作成・スキーマ作成
```

2. 日次 ETL を実行（市場カレンダー・株価・財務を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3. 特徴量（features）を作成
```python
from datetime import date
from kabusys.strategy import build_features

cnt = build_features(conn, target_date=date.today())
print(f"features upserted: {cnt}")
```

4. シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

signals_count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {signals_count}")
```

5. ニュース収集ジョブ実行（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は valid な銘柄コードの set (例: {"7203", "6758", ...})
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

6. J-Quants のデータを直接取得して保存する例
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# トークンは settings.jquants_refresh_token を使って自動取得されます
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

注: 各処理は冪等（同日付のデータは置換／更新）を意識して実装されています。

---

## 環境変数の自動読み込みについて

- パッケージの起動時に、自動でプロジェクトルート（.git または pyproject.toml を基準）を探し `.env` → `.env.local` の順に読み込みます。
- 読み込みの優先順位: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを抑制したい場合は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイルと役割（src/kabusys 以下）:

- __init__.py
  - パッケージ初期化。エクスポートモジュール: data, strategy, execution, monitoring

- config.py
  - 環境変数 / 設定管理（Settings クラス）

- data/
  - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存ユーティリティ）
  - news_collector.py — RSS フェッチ / 前処理 / raw_news 保存 / 銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — zscore_normalize の公開ラッパー
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - calendar_management.py — market_calendar の管理 / 営業日ロジック
  - audit.py — 監査ログテーブル DDL（signal_events, order_requests, executions 等）

- research/
  - factor_research.py — ファクター計算（momentum / volatility / value）
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

- strategy/
  - feature_engineering.py — ファクターの正規化・フィルタリング・features テーブルへの UPSERT
  - signal_generator.py — features と ai_scores を統合して売買シグナル生成
  - __init__.py — build_features, generate_signals のエクスポート

- execution/
  - 発注 / execution 層用モジュール（現状ファイルは空または実装されているファイルに依存）

- monitoring/
  - 監視・アラート関連モジュール（Slack 通知等を想定）

- その他
  - research/__init__.py, data/__init__.py, strategy/__init__.py などで公開 API を整備

（上記はコードベースに含まれる主要モジュールの要約です。細かな補助関数や定数については各ファイルの docstring を参照してください。）

---

## 運用・注意点

- データ整合性
  - DuckDB のテーブルは多くが NOT NULL / CHECK 制約や PRIMARY KEY を持ちます。保存前のデータ整合性に注意してください。
- レート制御 / リトライ
  - J-Quants クライアントは 120 req/min のレート制限を想定した固定間隔スロットリングと指数バックオフを備えています。
- セキュリティ
  - news_collector では SSRF 対策（スキーム検証・プライベートホスト排除・リダイレクト検査）や XML 安全処理（defusedxml）を実装しています。
- 本番運用
  - KABUSYS_ENV を `paper_trading` / `live` に切り替えて運用区分を分離してください。
  - 発注 / 実際のブローカー連携部分は別途実装・監査が必要です。

---

## 開発者向け補足

- 型注釈や docstring を積極活用しているため、IDE の補完や静的解析（mypy, flake8）でのチェックが有効です。
- DB スキーマは schema.py に集中しているため、テーブル追加はまずそこを更新してください。
- テスト：各ネットワーク I/O 部分（HTTP, urllib）や _urlopen, _RateLimiter, get_id_token などはモックしやすい作りになっています。

---

もし README に追加して欲しい内容（例：具体的なユースケース、CI / テスト手順、デプロイ手順、例 .env.example）や、英語版を希望される場合は教えてください。