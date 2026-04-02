# KabuSys

KabuSys は日本株向けのデータパイプライン、研究（リサーチ）、AI を使ったニュース解析、監査ログなどを備えた自動売買システムのライブラリ群です。本リポジトリは、J-Quants / JPX / RSS / OpenAI (gpt-4o-mini) 等を組み合わせて、データ収集・品質チェック・ファクター計算・AI スコアリング・市場レジーム判定・監査ログ初期化等を行えるように設計されています。

主な設計方針：
- ルックアヘッドバイアス防止（内部で datetime.today() を直接参照しない等）
- DuckDB を中心にした ETL / 保存（冪等保存を重視）
- 外部 API 呼び出しにはリトライ・レート制御・フェイルセーフを実装
- テスト容易性（API 呼び出し箇所はモック差し替え可能）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ（設定値バリデーション）

- データ（data）
  - J-Quants API クライアント（価格・財務・カレンダー取得、保存用関数）
  - ETL パイプライン（run_daily_etl 等）
  - カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS 取得・前処理・保存、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化（監査テーブル・インデックス定義・init 関数）
  - 汎用統計ユーティリティ（Zスコア正規化）

- AI（ai）
  - ニュースのセンチメントスコアリング（news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）（regime_detector.score_regime）

- Research（research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC 計算、統計サマリー等の解析ユーティリティ

- その他
  - 監視設定（CPU/メモリ/ディスクしきい値を環境変数で指定可能）
  - Audit DB 初期化ユーティリティ

---

## 必要条件

- Python 3.10 以上（型注記に | 演算子を使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

実行環境や機能を多く使う場合は追加パッケージが必要になる可能性があります（例：Slack 通知機能を有効にする場合は Slack SDK を追加で使う実装を行ってください）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください）
   - pip install -e .  (パッケージ化されている場合)

4. 環境変数 / .env の準備
   - プロジェクトルートに .env （または .env.local）ファイルを置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主に必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...         (score_news / regime_detector で使用)
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   .env のパースはシェル形式（コメント・シングル/ダブルクォート・export 表記）に対応しています。

---

## 使い方（簡単な例）

以下は基本的な使い方の例です。実際にはロギング設定や例外処理を追加してください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH を反映
db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアの実行

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(<your_duckdb_path>))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を参照
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("<db_path>")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ（audit）スキーマの初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

- 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore_normalize 等で正規化して利用
```

注意点:
- score_news / score_regime の OpenAI 呼び出しはネットワークや API の失敗が起こりうるため、ログやリトライ挙動を確認してください。
- ETL の J-Quants 呼び出しは API レート制限（120 req/min）・認証処理・リトライを内包しています。JQUANTS_REFRESH_TOKEN を正しく設定してください。

---

## 自動 .env 読み込みについて

- プロジェクトルートはこのパッケージの file location を基点に上位ディレクトリを探索して .git または pyproject.toml を検出して決定します（CWD に依存しません）。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なモジュール一覧（抜粋）です。

- kabusys/__init__.py
- kabusys/config.py
- kabusys/ai/
  - __init__.py
  - news_nlp.py            — ニュースの NLP スコアリング
  - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
- kabusys/data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント + 保存ユーティリティ
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - news_collector.py      — RSS ニュース収集・前処理
  - quality.py             — データ品質チェック
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログテーブル定義・初期化
- kabusys/research/
  - __init__.py
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー 等

（上記以外にも strategy / execution / monitoring 等のサブパッケージが __all__ に含まれる設計になっており、将来的な拡張を想定しています。）

---

## 開発・テスト時のヒント

- OpenAI 呼び出し部分（news_nlp._call_openai_api / regime_detector._call_openai_api）はテスト用にモックしやすいように分離されています。
- DuckDB を使ったテストは ":memory:" を指定してインメモリ DB を利用できます。
- ETL / 保存系関数は冪等設計（INSERT ... ON CONFLICT DO UPDATE）になっています。部分失敗時のデータ保護を意識した実装です。

---

## ライセンス・注意事項

- 本 README はリポジトリに含まれるコードに基づくドキュメントです。実際の運用では API キーや機密情報の管理、発注ロジックの安全性（重複発注防止、リスク管理）を十分に確認してください。
- 実際の売買に使用する際は paper_trading など検証環境で十分に動作確認を行ってから live 環境へ移行してください（KABUSYS_ENV を活用）。

---

必要があれば、README に含めるサンプル .env.example、実行スクリプト（CLI）や追加のセットアップ（systemd / Supervisor 用例）、各モジュールの API リファレンスを追記できます。どの情報を優先して追加しましょうか？