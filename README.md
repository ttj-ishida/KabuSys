# KabuSys

日本株自動売買プラットフォームのコアライブラリ（軽量なデータプラットフォーム・リサーチ・AI 評価・監査ログ機能を含む）。

このリポジトリは、J-Quants / kabuステーション 等のデータソース・ブローカーと連携し、
DuckDB を中心とした ETL / 品質チェック / ファクター計算 / ニュース NLP / レジーム判定 / 監査ログ機能を提供します。

主な設計方針:
- ルックアヘッドバイアス防止（内部で date.today() などを不用意に参照しない）
- DuckDB を利用した高速な SQL 処理（ETL/計算は SQL + 最小限の Python）
- 外部 API 呼び出しに対する堅牢なリトライ・レート制御・フェイルセーフ
- 監査ログによるトレーサビリティ（UUID ベースの階層構造）

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` をプロジェクトルートから自動読み込み（必要に応じて無効化可）
  - 必須設定値は Settings オブジェクトで取得可能（kabusys.config.settings）

- データ ETL（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダーの取得・保存
  - レート制限・トークン自動リフレッシュ・ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT）

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue オブジェクトで報告）

- カレンダー管理
  - 営業日判定・前後営業日の検索・期間内営業日取得
  - 夜間バッチによるカレンダー更新ジョブ

- ニュース収集と NLP
  - RSS フィードの安全な収集（SSRF 対策、XML 処理の安全化、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（ai_scores テーブルへの書込み）
  - レスポンス検証・バッチ化・リトライ

- 市場レジーム判定
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）判定
  - OpenAI 呼び出し時のリトライ・フェイルセーフ（失敗時は中立扱い）

- 研究用ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - 監査 DB 初期化ユーティリティ（DuckDB）

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の型記法などを使用しているため）
- 主な依存パッケージ:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）
- J-Quants / OpenAI / kabuステーション 等の API キー

pip インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# またはパッケージ化されていれば: pip install -e .
```

---

## 環境変数 (.env)

プロジェクトルートの `.env` / `.env.local` を自動読み込みします（優先順位: OS 環境 > .env.local > .env）。
自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数（kabusys.config.Settings に準拠）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール実行時に必要）

例 `.env.example`:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
```
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# またはプロジェクトに setup/pyproject があれば:
# pip install -e .
```

2. 必要な環境変数を設定（`.env` をプロジェクトルートに作成）
   - 上記の `.env.example` を参考に必須キーを埋める

3. データディレクトリを作成（設定に応じて）
```
mkdir -p data
```

4. 監査 DB を初期化（任意: 発注・監査ログを使う場合）
Python REPL またはスクリプトから:
```python
from pathlib import Path
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# 例: settings.duckdb_path を使用して監査 DB を初期化
conn = init_audit_db(settings.duckdb_path)
# あるいはファイルパス指定:
# conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主な API と利用例）

以下はライブラリを直接インポートして利用する例です。実運用では CLI やジョブランナーから呼び出すことを想定しています。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを一括）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコア付け
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数に設定しておく、または api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
norm = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 注意点・運用上のヒント

- OpenAI 呼び出しや外部 API 呼び出しは料金・レート制限に注意してください。実行時は必ず適切な API キーとコスト管理を行ってください。
- ETL や AI スコア処理は非同期バッチ・スケジューラ（cron / Airflow 等）から定期実行することを想定しています。
- settings.env により稼働モードを切り替え可能:
  - KABUSYS_ENV=development / paper_trading / live
  - settings.is_live / is_paper / is_dev を利用してコード内で分岐可能
- 自動 .env ロードはプロジェクトルートを .git または pyproject.toml を起点に探索します。配布後も正しく動作する設計です。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py       — ニュース NLP（銘柄別スコア）
  - regime_detector.py— 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + DuckDB 保存
  - pipeline.py       — ETL パイプライン（run_daily_etl 等）
  - etl.py            — ETL インターフェース/型 (ETLResult)
  - stats.py          — 共通統計ユーティリティ（zscore_normalize）
  - quality.py        — データ品質チェック
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py — RSS ニュース収集（SSRF/サイズ制限/正規化）
  - audit.py          — 監査ログ定義・初期化（signal/order/execution）
- research/
  - __init__.py
  - factor_research.py   — Momentum/Value/Volatility 等
  - feature_exploration.py — 将来リターン・IC・統計サマリー

（上記は主要モジュールの一覧であり、細かいモジュールやユーティリティも含まれます）

---

## 開発・テスト

- 自動ロードされる .env を利用するため、テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると外部環境の影響を避けられます。
- OpenAI 呼び出しなどはモック可能な設計（内部の _call_openai_api を patch する等）になっています。ユニットテストでは外部 API をモックしてください。

---

## ライセンス・貢献

（ここにライセンス情報・コントリビューションガイドを追加してください）

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。詳細は各モジュールの docstring（src/kabusys 以下）を参照してください。必要があればサンプルスクリプトや CLI を追加して提供できます。