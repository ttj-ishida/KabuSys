# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL・データ品質チェック・ニュース収集・AIによるニュースセンチメント、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・分析・監査・戦略評価を行うためのモジュール群です。  
主に以下の関心事をカバーします。

- J-Quants API からのデータ取得（株価日足、財務、上場情報、マーケットカレンダー）
- DuckDB によるデータ格納と冪等保存（ON CONFLICT）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と前処理、ニュースと銘柄の紐付け
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメント（レジーム判定）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）および統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- システム設定の環境変数管理（.env 自動読み込み機能）

設計上の重要点として「ルックアヘッドバイアス回避（過去データのみ参照）」「API呼び出しのリトライ/フェイルセーフ」「DuckDB での冪等保存」が重視されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、認証リフレッシュ、レート制限、DuckDB 保存関数）
  - pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - news_collector: RSS 取得・前処理・raw_news への冪等保存
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - stats: Zスコア正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントの付与（ai_scores）
  - regime_detector.score_regime: ETF（1321）MA乖離とマクロニュースの LLMセンチメントを合成して市場レジーム（bull/neutral/bear）を判定（market_regime）
- research/
  - factor_research: mom/value/volatility 等のファクター計算（DuckDB 給データ）
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク関数
- config:
  - 環境変数読み込み（.env / .env.local の自動読み込み）、各種設定プロパティ

---

## 前提 / 依存関係（代表）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （ネットワーク: J-Quants API, OpenAI API, RSSソース）

実際の環境ではこれらに加えてログ設定や sqlite（監視用）などが必要になることがあります。

---

## セットアップ手順

1. リポジトリをクローン / ローカルに配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements ファイルがある場合はそれを使用してください）

4. パッケージをローカルインストール（開発モード）
   - pip install -e .

5. 環境変数 / .env の準備
   プロジェクトルートに `.env` または `.env.local` を配置すると自動的に読み込まれます（読み込み順: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要 API と実行例）

以下は Python REPL やスクリプトから直接呼び出す際の簡単な例です。

- 設定読み込み（Settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作成して ETL を実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（銘柄別）を生成
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が .env にあれば api_key は省略可
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームを判定して保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order / signal / execution の操作が可能
```

- 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

- データ品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

ログやエラーは Python の logging を通じて出力されます。実運用では適切な logging 設定を行ってください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants 用リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視・プロセスマネジャ用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 実行環境 ('development' | 'paper_trading' | 'live')
- LOG_LEVEL: ログレベル ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')

env 読み込みに関する補足:
- .env と .env.local をプロジェクトルート（.git または pyproject.toml がある階層）で自動読み込みします。
- 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要なモジュール構成 (src/kabusys 以下) は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースセンチメント（銘柄別）
    - regime_detector.py         # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント + DuckDB 保存
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - etl.py                     # ETLResult 型の再エクスポート
    - news_collector.py          # RSS ニュース収集
    - calendar_management.py     # JPX カレンダー管理・営業日判定
    - quality.py                 # データ品質チェック
    - stats.py                   # 統計ユーティリティ（zscore 等）
    - audit.py                   # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         # ファクター計算
    - feature_exploration.py     # 将来リターン、IC、統計サマリー
  - monitoring/ (将来的に監視/実行モジュールが入る想定)
  - strategy/ (戦略実装用プレースホルダ)
  - execution/ (発注ロジック用プレースホルダ)

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアス防止:
  - モジュールの多くは target_date パラメータに明示的に依存し、date.today() などを直接参照しない設計になっています。バックテストや過去日再現の際は必ず target_date を指定してください。
- 秘匿情報:
  - API キーやトークンは .env ファイルに保存する場合、適切なファイル権限で管理してください。.env は一般にバージョン管理から除外します。
- エラーハンドリング:
  - 外部 API 呼び出しはリトライやフォールバック（スコア 0.0 など）を行う設計ですが、重大な障害はログに出力されます。運用モニタリングが重要です。
- DuckDB の互換性:
  - 一部の実装は DuckDB の executemany の挙動（空リスト不可等）やバインドの違いを考慮しています。DuckDB のバージョンにより振る舞いが変わる可能性があるため、運用時はバージョン固定を推奨します。

---

## 参考 / 開発メモ

- テスト: 各モジュールは外部 API を呼ぶためユニットテスト時はネットワーク呼び出しをモックすることを想定しています（コード中に patch 用の注記あり）。
- ロギング: モジュールは logging.getLogger(__name__) を使用しており、アプリ側でハンドラ / レベルを設定してください。
- 拡張: strategy、execution、monitoring モジュールはプレースホルダとして用意されています。ブローカ接続・発注ロジックはここに実装してください。

---

必要であれば、セットアップ用の requirements.txt、具体的なサンプルスクリプト、または Dockerfile / systemd ユニットファイル等のテンプレートも作成できます。どれを優先しますか？