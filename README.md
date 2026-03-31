# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買/リサーチ用ユーティリティ群をまとめた Python ライブラリです。  
J-Quants からのデータ取得・ETL、ニュースの収集と LLM によるニューススコアリング、ファクター計算、監査ログスキーマ等を提供します。

主な設計方針：
- ルックアヘッドバイアスを排除する（内部で date.today() を直接参照しない設計の関数が多く含まれます）
- DuckDB を中核に据えたローカル分析 / ETL ワークフロー
- 外部 API 呼び出し（J-Quants / OpenAI）は再試行・レート制御・フェイルセーフを実装
- 冪等性（同じデータを何度実行しても安全に保存できる）を重視

---

## 機能一覧

- 環境変数・設定の管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
- データ ETL（kabusys.data.pipeline / etl）
  - J-Quants からの株価・財務・カレンダー差分取得と DuckDB への保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出しラッパ、トークン自動リフレッシュ、レートリミット、ページネーション対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、正規化、SSRF 対策、raw_news テーブルへの冪等保存を想定
- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティ用スキーマ作成ユーティリティ
- 統計ユーティリティ（kabusys.data.stats）
  - Zスコア正規化など研究で使う汎用関数
- 研究モジュール（kabusys.research）
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク変換
- ニュース NLP と市場レジーム判定（kabusys.ai）
  - gpt-4o-mini を用いたニュースセンチメント計算（score_news）
  - ETF（1321）の MA200 乖離とマクロニュースの組合せによる市場レジーム判定（score_regime）
- ETL 実行結果と品質検査の集約（ETLResult）

---

## セットアップ手順

1. Python 仮想環境を作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なパッケージ（主に）：duckdb, openai, defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

3. プロジェクトを編集可能モードでインストール（任意）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます（デフォルト、CWD 依存せずプロジェクトのルートを .git または pyproject.toml で検出）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の主な環境変数（コード中で _require により必須とされるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注等を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャネル

外部 API 関連:
- OPENAI_API_KEY — OpenAI（news_nlp, regime_detector）を使う場合に必要。関数は api_key 引数でも受け取れます。

任意またはデフォルト値を持つ環境変数:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL — デフォルト INFO
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視用設定

例 `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

基本的に DuckDB 接続を作り、公開された関数を呼び出します。

- ETL（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# score_news は api_key 引数を通して明示的にキー注入可能
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を利用
print("書込銘柄数:", n_written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
res = score_regime(conn, target_date=date(2026, 03, 20))
```

- 監査 DB 初期化（監査ログ専用 DB を作成してスキーマを適用）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査テーブルへアクセス可能
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点：
- AI（OpenAI）や J-Quants API を使う処理はネットワーク接続と API キーが必要です。テスト時は api_key 引数経由でキー注入、または該当関数の内部 API 呼び出しをモックできます（コード中で想定されています）。
- 多くの関数はルックアヘッドバイアスを避けるため、明示的な target_date を受け取ります。内部で date.today() を参照しないよう設計されていますが、ETL のトップレベル呼び出し run_daily_etl では省略時に今日が使われます。

---

## ディレクトリ構成（主要ファイル）

※ このリポジトリは src/ 配下にパッケージを置く構成です。

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、settings オブジェクトを提供
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM ベース評価（score_news）
    - regime_detector.py  — MA200 とニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py         — ETL パイプラインと run_daily_etl
    - etl.py              — ETLResult の公開再エクスポート
    - jquants_client.py   — J-Quants API クライアントと保存ロジック
    - news_collector.py   — RSS 収集・正規化・SSRF 対策
    - calendar_management.py — 市場カレンダーの管理と営業日判定
    - quality.py          — データ品質チェック（欠損・重複・スパイク等）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログ（signal/order/execution）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク関数
  - （将来的／別パッケージ）
    - strategy, execution, monitoring 等（プロジェクトルート __init__ では公開候補として挙がっていますが、上記ソースに含まれるモジュールを優先してください）

---

## 開発・運用 Tips

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を走査して `.env` / `.env.local` を読み込みます。テストなどで自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や J-Quants の呼び出しは再試行・バックオフ・フェイルセーフを備えていますが、API の利用料やレート制限には注意してください。
- DuckDB はスキーマ設計上、executemany の空リストを受け付けないバージョン差に配慮した実装がされています。直接 SQL を投げる際は空のパラメータに注意してください。
- ニュース収集では SSRF 保護（ホストのプライベート判定、リダイレクト検査等）やレスポンスサイズ制限を実装していますが、外部からのフィードを扱う運用時は追加の監視・検証を推奨します。

---

## ライセンス / 貢献

README に記載のない点（テスト、CI、パッケージ化、依存関係の固定等）はプロジェクトのポリシーに従ってください。Issue / PR ベースでの改善を歓迎します。

---

質問や README に追加してほしいサンプル（例：より詳しい ETL 実行例や DB スキーマ定義の抜粋）があれば教えてください。