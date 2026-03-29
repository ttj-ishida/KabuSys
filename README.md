# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ ETL、ニュース NLP、リサーチ（ファクター計算）、市場レジーム判定、監査ログなど、売買システムに必要な基盤機能を提供します。

主な目的は「バックテスト／リサーチ環境と本番運用の間にある共通処理を高品質に実装すること」です。Look‑ahead bias や冪等性、API レート制御、フェイルセーフ設計に配慮した実装になっています。

## 主な機能一覧

- 環境設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）と必須変数チェック
- データ ETL（J‑Quants 経由）
  - 株価（日足）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - レート制限・リトライ・ID トークン自動更新対応
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集 / NLP
  - RSS からのニュース収集（SSRF・XML 攻撃対策、トラッキング除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメントスコアリング（score_news）
  - マクロニュース + ETF MA による市場レジーム判定（score_regime）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査（Audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル定義・初期化（DuckDB）
  - 冪等キー・ステータス管理
- ユーティリティ
  - DuckDB を用いたローカルデータ管理
  - 安全な RSS パーシング（defusedxml）や URL 正規化など

---

## 動作要件

- Python 3.10+
- 必要な外部パッケージ（主要）
  - duckdb
  - openai
  - defusedxml

（用途により slack SDK など追加の依存が必要になることがあります）

例（最小セット）:
```
pip install duckdb openai defusedxml
```

パッケージ開発・配布をする場合は setup / pyproject を利用してインストールしてください。ソースは `src/` 配下にパッケージとして配置されています。

---

## 環境変数 / .env

主要な必須環境変数:

- JQUANTS_REFRESH_TOKEN — J‑Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知用チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必須）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）

挙動:

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` → `.env.local` を自動読み込みします（環境変数が優先されます）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須値が未設定の場合は Settings のプロパティアクセスで `ValueError` が発生します（早期検出）。

---

## セットアップ手順（ローカル）

1. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。

3. 環境変数を用意（.env をプロジェクトルートに作成）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   ```

4. DuckDB 用ディレクトリを作る（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（主要 API 例）

下記は最小の利用例（Python スクリプトや REPL で実行）。

- DuckDB 接続を作成して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定しない場合は今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（score_news）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OpenAI API キーを環境変数 OPENAI_API_KEY にセットしておくか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジームを判定（score_regime）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 以降、conn を使って監査テーブルが利用可能
```

- 設定値参照例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。テスト時は公開されている内部呼び出し関数をモックすることが推奨されます（コード中に patch を想定した箇所があります）。
- ETL / データ取得は外部 API（J‑Quants）を呼びます。`JQUANTS_REFRESH_TOKEN` が必須です。

---

## よくある操作

- 自動 .env 読み込みを無効化してテストする:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- ログレベルを変更
  ```
  export LOG_LEVEL=DEBUG
  ```

- 本番運用判定
  ```
  export KABUSYS_ENV=live
  ```

---

## ディレクトリ構成（主要ファイル）

下記はパッケージ内の主要モジュール構成です（src/kabusys）:

- __init__.py
- config.py
  - 環境設定読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py — 銘柄ごとのニュースセンチメント算出（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - jquants_client.py — J‑Quants API クライアント（取得 + DuckDB への保存）
  - news_collector.py — RSS 収集（SSRF 対策など）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit.py — 監査（signal/order/execution）スキーマ + 初期化
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリーなど

（リポジトリの root には pyproject.toml / .git / .env.example などが想定されます）

---

## 設計上の注意点 / 方針（抜粋）

- Look‑ahead bias を避けるため、内部で datetime.today() や date.today() を無闇に参照せず、関数引数で基準日を明示する設計が採られています。
- API 呼び出しはリトライ・バックオフ・レート制御を実装し、外部障害に対するフェイルセーフ（失敗時はスキップして継続）を意識しています。
- DuckDB への保存は冪等（ON CONFLICT / DO UPDATE）を基本としています。
- RSS / XML 処理は脆弱性対策（defusedxml、SSRF チェック、最大受信サイズ制限）を実施しています。

---

## テスト / モック

- 外部 API（OpenAI / J‑Quants / RSS）呼び出し箇所はテスト時にモックすることを想定した作りになっています（内部で関数を差し替えやすく実装）。
- 環境変数自動ロードを無効化するフラグがあるため、ユニットテストでの環境制御が容易です。

---

この README はコードベースの概要と主要な使い方をまとめたものです。各モジュール内に詳細な docstring と設計コメントがありますので、実装を参照しながら使用・拡張してください。質問や追加のドキュメント化希望があれば教えてください。