# KabuSys

日本株向けの自動売買 / データプラットフォームのライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、研究（ファクター計算・特徴量解析）、AI を用いたニュースセンチメント評価、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）などを含みます。

---

## 主要コンセプト（概要）

- データ層（data）: J-Quants からの株価・財務・カレンダー取得、RSS ニュース収集、DuckDB への冪等保存、品質チェック、マーケットカレンダー管理、監査ログ初期化。
- 研究層（research）: ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン計算、IC 計算、統計サマリ。
- AI 層（ai）: OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）とマクロニュースを統合した市場レジーム判定。
- 設定管理: .env または環境変数からの設定読み込み、自動読み込み（プロジェクトルート検出）。
- 安全性・運用面: レートリミッター、リトライ、SSRF 対策、Look-ahead バイアス回避の設計、冪等保存。

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足、財務、上場銘柄情報、マーケットカレンダー）
  - RSS フィードからのニュース収集（SSRF/サイズ制限/トラッキング除去）
- ETL
  - 差分取得（最終取得日からの差分）
  - DuckDB への冪等保存（ON CONFLICT）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質管理
  - 欠損チェック、重複チェック、スパイク検出、日付整合チェック
  - 全チェック実行 run_all_checks
- 研究 / ファクター計算
  - モメンタム、ボラティリティ、バリューなどの定量ファクター
  - 将来リターン計算、IC（スピアマン）計算、Z スコア正規化
- AI（OpenAI）
  - ニュースのセンチメント評価（銘柄単位、JSON Mode）
  - マクロニュースと MA 乖離を合成して市場レジーム（bull/neutral/bear）判定
  - API 呼び出しはリトライ・フォールバック実装
- 監査（Audit）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化
  - 監査 DB の初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - .env 自動読み込み（プロジェクトルートを検出）
  - 必須環境変数の検証

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそれに従ってください）

---

## インストール（開発環境）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix/macOS) または .venv\Scripts\activate (Windows)

2. パッケージのインストール（例）
   - pip install duckdb openai defusedxml

3. パッケージを編集可能モードでインストール（プロジェクトルートで）
   - pip install -e .

---

## 設定（環境変数 / .env）

自動的にプロジェクトルート（.git または pyproject.toml を探索）配下の `.env` / `.env.local` を読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須・デフォルト値等）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に未指定時に参照）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

.env の例（.env.example を参照して作成してください）:
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単なコード例）

以下は Python から直接機能を呼び出す例です。適宜仮想環境・環境変数を設定してください。

- DuckDB に接続して日次 ETL を走らせる
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- AI ニュースセンチメント（銘柄別）をスコアリング
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key=None で OK
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

- 市場レジーム判定を実行（1321 の MA200 乖離 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: でメモリ DB も可
```

- RSS フィードを取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しには環境変数 `OPENAI_API_KEY` を設定するか api_key 引数にキーを渡してください。
- ETL / AI 処理はネットワーク・API 依存です。API レートや課金に注意して実行してください。
- DuckDB の書き込みはトランザクション管理を行いますが、呼び出し側でも適切な接続管理を行ってください。

---

## 実運用上のポイント

- Look-ahead バイアスに配慮した設計:
  - 各モジュールは内部で date を明示的に与えることを推奨し、datetime.today()/date.today() を内部で参照しないよう配慮。
  - ニュースウィンドウや MA 計算は target_date 未満のデータのみを参照する仕様です。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT を使って冪等にしてあります（raw_prices, raw_financials, market_calendar など）。
  - 監査ログの order_request_id は冪等キーとして発注重複を防止する前提です。
- フォールバック / フェイルセーフ:
  - OpenAI の呼び出し失敗時は安全側の0.0スコアにフォールバックする等、処理を継続する実装が多くあります。
- セキュリティ:
  - RSS 取得は SSRF 対策、受信サイズ制限、XML パースに defusedxml を使用。
  - J-Quants 認証はリフレッシュトークンフローで自動更新（401 時に 1 回リフレッシュ）。

---

## ディレクトリ構成（要旨）

（パッケージルート: src/kabusys/ 以下を抜粋）

- __init__.py — パッケージ基本情報（バージョン等）
- config.py — 環境変数 / .env 読み込み、Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースの銘柄別センチメント評価（OpenAI）
  - regime_detector.py — マクロニュース + MA200 を用いた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、取得・保存ロジック
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py — RSS 収集・前処理
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - calendar_management.py — JPX カレンダー管理、営業日判定、calendar_update_job
  - audit.py — 監査ログ（DDL・初期化ユーティリティ）
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ等
- その他: strategy / execution / monitoring といったサブパッケージを想定して公開（__all__）

---

## 開発・テスト

- モジュール単位でのユニットテストを推奨（OpenAI / 外部 API 呼び出しはモック化）。
- news_collector、jquants_client、OpenAI 呼び出しなどは外部依存が多いため、ネットワーク部分は patch / monkeypatch / unittest.mock を用いた隔離テストが望ましい。
- 環境変数読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してテスト用に制御。

---

## 参考・補足

- 必要な権限や API クレデンシャルはプロジェクト外で管理してください（.env を git 管理しない等）。
- 本 README はコードベースに含まれる docstring / 設計方針を要約しています。各モジュールの docstring を参照すると詳細な挙動・仕様（エッジケース、ログメッセージ、例外処理など）が記載されています。

---

問題や追加したい内容（例: CLI、サンプルスクリプト、docker 化方法など）があれば教えてください。README に追記してまとめます。