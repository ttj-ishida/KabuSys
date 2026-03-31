# KabuSys

日本株向けのデータ基盤・研究・自動売買を想定したライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集とLLMによるニュースNLP、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注/約定トレース）などを含みます。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」です。DB は DuckDB を想定しており、OpenAI（gpt-4o-mini）をニュース解析に使用します。

---

## 主な機能

- データ収集（ETL）
  - J-Quants API から株価日足・財務・マーケットカレンダーを差分取得・保存（DuckDB）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集と NLP
  - RSS からニュースを収集し raw_news に保存、銘柄紐付け
  - OpenAI を用いた銘柄別センチメント（ai_scores）算出（バッチ処理・再試行・バリデーション）
- 市場レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して日次で bull/neutral/bear を判定
- 研究用モジュール
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）や統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ（冪等）
- 設定管理
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出、.env.local 優先、無効化可能）

---

## 動作環境（推奨）

- Python 3.10+
- 必要パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- （ネットワークアクセスが必要）J-Quants API と OpenAI API 用の鍵

パッケージ化・依存管理はプロジェクトの pyproject.toml / requirements.txt に従ってください。

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux)
   - .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがあればそれを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定します。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

5. DuckDB データファイル格納先ディレクトリ等を準備
   - デフォルトでは data/kabusys.duckdb を使用します。必要に応じてディレクトリを作成してください。

---

## 環境変数 (.env の例)

以下は主要な環境変数の例です。最低限 J-Quants と OpenAI のキーが必要になります。

```
# J-Quants
JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン

# kabuステーション（必要なら）
KABU_API_PASSWORD=...

# OpenAI / News NLP
OPENAI_API_KEY=sk-...

# Slack 通知（必要なら）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベースパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行監視設定（任意）
PID_FILE_PATH=data/execution.pid
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0

# 実行環境
KABUSYS_ENV=development  # development / paper_trading / live
LOG_LEVEL=INFO
```

注意:
- パッケージは .env と OS 環境変数両方を参照します。`.env.local` は `.env` より優先して読み込まれます。
- 自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## 使い方（代表的な例）

以下は主要ユースケースの簡単な実行例です。コードは Python REPL やスクリプトで実行してください。

- DuckDB 接続の準備例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 例: 今日の日付で ETL を実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を算出する:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date に対応するニュースウィンドウ（前日15:00 JST ～ 当日08:30 JST）を対象に実行
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"スコアを付与した銘柄数: {count}")
```

- 市場レジーム判定を実行する:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DuckDB を初期化する（監査スキーマの作成）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成されます
```

- 研究モジュールの利用例（ファクター計算）:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
# 結果は [{"date": ..., "code": "XXXX", "...": ...}, ...]
```

- Z スコア正規化ユーティリティ:

```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

---

## よく使うポイント・注意事項

- ルックアヘッドバイアス防止
  - 多くの関数は内部で date.today() を直接参照せず、呼び出し側が target_date を渡す設計です。バッチやバックテストでは意識して target_date を指定してください。
- OpenAI 呼び出し
  - API 呼び出しは再試行・バリデーション・JSON モードを利用して結果を厳密に扱います。レスポンスの不正や API エラー時はフェイルセーフ（0 やスキップ）で継続する設計です。
- ETL の冪等性
  - DuckDB への保存は可能な限り ON CONFLICT DO UPDATE（冪等）で実装されています。部分失敗時の保護（既存データの消失回避）にも配慮しています。
- RSS フィード取得の SSRF 対策
  - ニュース取得はリダイレクト先の検査やプライベートIPブロック、レスポンスサイズ制限などの安全対策を実装しています。
- 自動 .env 読み込み
  - パッケージインポート時にプロジェクトルート（.git か pyproject.toml がある場所）を探索して .env / .env.local を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（主なファイル）

（パスはリポジトリ内の src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント算出（OpenAI）
    - regime_detector.py — ETF MA とニュースセンチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py        — ETL パイプライン（run_daily_etl など）
    - jquants_client.py  — J-Quants API クライアント（取得/保存ロジック）
    - etl.py             — ETLResult の再エクスポート
    - stats.py           — zscore 正規化など統計ユーティリティ
    - quality.py         — データ品質チェック群
    - news_collector.py  — RSS 収集・前処理・保存ロジック
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py           — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

---

## 開発・テスト

- 自動ロードされる .env を避けてテストしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワークを伴う外部依存は unittest.mock で差し替えてテスト可能です。コード内で _call_openai_api 等を patch する設計になっています。

---

README は以上です。必要であれば以下を追記します：
- 具体的な依存パッケージの固定バージョン（requirements.txt）
- CI / 実行スケジュール例（cron / systemd timer）
- Slack 通知や実行監視の使用例
- 詳細な DB スキーマ一覧（DDL）