# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリセットです。  
主に以下を提供します。

- J-Quants API を用いたデータ ETL（株価・財務・カレンダー）
- ニュース収集・NLP（OpenAI を用いた銘柄センチメント評価）
- 市場レジーム判定（ETF + マクロニュースを統合）
- 研究用ファクター計算・特徴量分析ユーティリティ
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order → execution のトレース用スキーマ）
- DuckDB を中心とした永続化・冪等保存ロジック

この README では概要・機能一覧・セットアップ手順・使い方（簡単なコード例）・ディレクトリ構成を日本語でまとめます。

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 必要条件
- 環境変数 / 設定
- セットアップ手順
- 使い方（コード例）
- ディレクトリ構成
- 開発／運用上の注意

---

## プロジェクト概要

KabuSys は日本株用のデータ基盤と自動売買の基礎機能群を提供する Python ライブラリ群です。  
DuckDB をデータレイク／中間DB として利用し、J-Quants API からの差分 ETL、ニュース収集、LLM（OpenAI）を用いたニュースセンチメント評価、ファクター計算、品質チェック、監査ログスキーマなどを備えています。  
設計方針として「ルックアヘッドバイアスの回避」「冪等性」「フェイルセーフ」を重視して実装されています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・取得・保存・レート制御・リトライ）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、追跡パラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化 / スキーマ（signal_events / order_requests / executions）
  - 統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI でスコア化し ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込み
  - リトライ・バックオフ・レスポンス検証を備えた LLM 呼び出し
- research/
  - ファクター算出（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - Settings: 環境変数管理、.env 自動ロード（プロジェクトルート基準）と保護機能

その他、監視・実行・戦略関連のエントリポイントを想定した構成が含まれます（execution や monitoring モジュール等）。

---

## 必要条件

- Python 3.10 以上（型注釈で | を使用しているため）
- パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）

requirements.txt がない場合は上記を pip でインストールしてください。例:

```bash
pip install duckdb openai defusedxml
```

（実際のプロジェクトでは pyproject.toml / requirements.txt を準備してください）

---

## 環境変数 / 設定

config.Settings を通じて環境変数を参照します。主なキー:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須で使用箇所あり）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（例: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH 等: 監視用設定
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)
- LOG_LEVEL: ログレベル (DEBUG/INFO/...)

自動で .env / .env.local をプロジェクトルートからロードします（os 環境変数が優先）。自動ロードを無効化するには:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

必須値が未設定の場合は Settings のプロパティで ValueError が発生します。

---

## セットアップ手順

1. リポジトリをチェックアウト

2. 仮想環境作成（推奨）および依存関係インストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

3. 環境変数を設定（.env を作成）

プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます。例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB の初期化（監査用 DB 初期化例）

Python REPL またはスクリプトで:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成
# conn は duckdb 接続オブジェクト
```

5. ETL 実行（サンプル）

後述の「使い方」を参照してください。

---

## 使い方（代表的なコード例）

ここでは基本的な操作の例を示します。実行前に必ず環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続を開く / ETL を実行する

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は today が使われる
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメント（ai.news_nlp.score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は duckdb 接続
written = score_news(conn, target_date=date(2026, 3, 19))  # 前日の15:00～当日08:30 JST ウィンドウ対象
print("書き込み銘柄数:", written)
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 19))
```

- 研究用ファクター計算（research）

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026, 3, 19))
vals = calc_value(conn, target_date=date(2026, 3, 19))
vols = calc_volatility(conn, target_date=date(2026, 3, 19))
```

- 監査スキーマ初期化（既存 conn に対して）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- J-Quants の ID トークン取得（内部で自動的に管理されるが直接呼び出しも可能）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル／モジュールです。

```
src/kabusys/
├─ __init__.py
├─ config.py                     # 環境変数・設定管理
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py                # ニュース NLP -> ai_scores
│  └─ regime_detector.py         # マーケットレジーム判定
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py          # J-Quants API クライアント + 保存関数
│  ├─ pipeline.py                # ETL パイプライン（run_daily_etl 等）
│  ├─ etl.py                     # ETLResult 再エクスポート
│  ├─ news_collector.py          # RSS ニュース収集（SSRF 対策等）
│  ├─ calendar_management.py     # マーケットカレンダー管理
│  ├─ quality.py                 # データ品質チェック
│  ├─ stats.py                   # 汎用統計（zscore_normalize 等）
│  ├─ audit.py                   # 監査ログスキーマ / 初期化
│  └─ ... (その他ユーティリティ)
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py         # Momentum/Value/Volatility 等
│  └─ feature_exploration.py     # forward returns, IC, summary, rank
└─ ai/                           # 上記参照
```

各ファイルには詳細な docstring と設計意図が記載されており、ルックアヘッドバイアス対策やエラー時のフォールバック戦略、冪等性設計などが述べられています。

---

## 開発／運用上の注意

- 環境値により本番（live）モードや paper_trading を切り替えられます。KABUSYS_ENV を慎重に設定してください（live モードは実際の発注や資金管理に関係する機能を有効にする想定）。
- OpenAI 呼び出しは外部 API を使用するためコストとレート制限があります。エラー時はフェイルセーフとして 0.0 スコアなどにフォールバックする実装になっていますが、運用時は API キーの安全管理と呼び出し量の監視を行ってください。
- J-Quants API はレート制限があります（コード内に RateLimiter 実装あり）。ID トークンの自動リフレッシュやリトライ実装があるものの、運用時は API 使用上限を必ず把握してください。
- news_collector は SSRF 対策（リダイレクト検査・プライベート IP 検査）や XML パースの安全対策（defusedxml）を行っていますが、追加でプロキシやネットワーク制御を導入することを推奨します。
- DuckDB の executemany の制約やバージョン差異（空リスト渡せない等）に注意するコードパターンが存在します。DuckDB のバージョンを更新する際は既存の動作確認を行ってください。
- 自動で .env をロードしますが、テスト時など自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

以上がこのコードベースの README.md（日本語）です。運用や機能追加の際に README の更新をご検討ください。必要であれば、セットアップスクリプト（Makefile / tox / pre-commit 設定）や requirements ファイル、サンプル .env.example のテンプレートも作成します。どの追加が必要か教えてください。