# KabuSys

KabuSys は日本株のデータパイプライン・リサーチ・AIスコアリング・自動売買監査を目的としたライブラリ群です。ETL による J-Quants からのデータ取得、ニュース収集と LLM を用いたニュースセンチメント評価、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存
  - 差分更新・バックフィル・ページネーション・レートリミット対応
- データ品質チェック
  - 欠損／重複／スパイク／日付不整合などのチェック機能
- ニュース収集
  - RSS フィードの安全な収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols テーブルに冪等保存
- AI ベースの NLP
  - ニュース記事のセンチメントスコアリング（gpt-4o-mini を想定、JSON Mode 利用）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを加重合成）
  - バッチ・リトライ・レスポンス検証・フェイルセーフ設計
- リサーチ / ファクター計算
  - Momentum / Volatility / Value などのファクター計算（DuckDB SQL + Python）
  - 将来リターン計算、IC（Spearman rank）や統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 の階層的トレーサビリティ用テーブルとインデックス定義
  - init_audit_db による初期化ユーティリティ
- ユーティリティ
  - 環境設定読み込み（.env / .env.local 自動読み込み、上書きルール）
  - 各種設定（DB パス、paper trading モード、監視閾値 など）

---

## 必要条件 / 依存パッケージ

- Python >= 3.10（型記法（|）と一部の構文を使用）
- 必要ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml

（実行環境やインストール方法に応じて追加パッケージが必要になる場合があります）

例: requirements.txt（プロジェクトに合わせて調整してください）
```
duckdb
openai
defusedxml
```

インストール例:
```bash
python -m pip install -r requirements.txt
# またはローカル開発
python -m pip install -e .
```

---

## 環境変数 / 設定

KabuSys は .env / .env.local または OS 環境変数を読み込みます（優先順位: OS 環境 > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

代表的な環境変数:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabu ステーション（発注等）
  - KABU_API_PASSWORD (必須) — kabu API 用パスワード
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OpenAI
  - OPENAI_API_KEY — LLM（news_nlp, regime_detector）で使用
- LINE 通知 (任意)
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベースパス（デフォルト値は project 内で指定）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- Paper Trading
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: "instant"）
- 監視 / 実行
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- システム環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL

設定オブジェクトは `kabusys.config.settings` からアクセスできます。
例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. Python 仮想環境を作成・有効化（推奨）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
```bash
python -m pip install -r requirements.txt
```

4. 環境変数を設定
- リポジトリルートに `.env` を作成するか、OS 環境変数を設定してください。
- 最低限必要: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- OpenAI を使う場合は OPENAI_API_KEY を設定

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
```

5. DuckDB データベースや監査 DB の初期化（必要に応じて）
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイルパスで初期化（親ディレクトリがなければ作成）
conn = init_audit_db("data/audit.duckdb")
conn.close()
```

---

## 使い方（例）

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニューススコア（ai）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", n_written)
conn.close()
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
conn.close()
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(momentum), "銘柄の結果")
conn.close()
```

- 監査スキーマ初期化（監査用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使用して order_events 等を挿入/参照
```

注意:
- AI 周り（news_nlp / regime_detector）は OpenAI API を使用するため `OPENAI_API_KEY` が必要です。API 呼び出し失敗時にはフェイルセーフ（スコアを 0 にする等）を行う実装になっています。
- ETL や API 呼び出しはネットワーク・認証依存なので、本番環境での実行前に .env の設定と DB スキーマを準備してください。

---

## 自動 .env 読み込みの挙動

- モジュールはパッケージルート（.git または pyproject.toml を上位に持つディレクトリ）を探索し、そのルートにある `.env` と `.env.local` を自動読み込みします。
- 読み込み順 / 上書きルール:
  - OS 環境変数（既存）を保護（上書きされない）
  - .env が読み込まれ、その後 .env.local が override=True で上書き
- 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みをスキップします。

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールの概略構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ma200 + macro news）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（is_trading_day, next/prev など）
    - etl.py — ETL の公開インターフェース（ETLResult）
    - pipeline.py — 日次 ETL パイプライン実装
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマ定義・初期化
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS ニュース取得・前処理・保存
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 開発上の注意 / 設計方針の抜粋

- ルックアヘッドバイアスの排除:
  - モジュール内部で datetime.today()/date.today() を直接参照しないよう設計されています。すべての処理は明示的に target_date を受け取るか、ETL のエントリポイントが日付を決定します。
- 冪等性:
  - J-Quants 保存処理や raw_news 保存は冪等性（ON CONFLICT / unique key）を考慮して実装されています。
- フェイルセーフ:
  - AI 呼び出し失敗や一部 API エラー時はスコアを 0 として継続するなど、全体処理が停止しない設計です。
- セキュリティ:
  - news_collector は SSRF 対策、XML パースの安全ライブラリ（defusedxml）を使用、受信サイズ制限などを実装しています。
- テスト容易性:
  - OpenAI 呼び出しなどは内部呼び出し関数を差し替えやすくしており、単体テストでモック可能です。

---

## サポート / 貢献

- バグ報告や機能提案は Issue を作成してください。
- 開発に貢献する場合は PR を送ってください。コーディング規約・テストを整えてからの送付を推奨します。

---

README はプロジェクト概要をまとめた簡易ドキュメントです。実際の運用や本番環境導入時は .env の管理、API キーの取り扱い、監視・ログの設定、十分なテストを行ってください。