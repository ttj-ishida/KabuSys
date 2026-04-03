# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants からの市場データ ETL、ニュース収集と LLM を用いたニュースセンチメント評価、マーケットレジーム判定、ファクター研究・特徴量探索、データ品質チェック、監査ログ（トレーサビリティ）など、運用・研究に必要な機能群を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API障害時の継続）」「外部 API 呼び出しの適切なレート制御／リトライ」です。

---

## 主な機能

- データ ETL（J-Quants からの差分取得、DuckDB への冪等保存）
  - daily prices、financial statements、market calendar 等
  - 差分取得、バックフィル、品質チェックを備えた日次パイプライン
- ニュース収集（RSS）と前処理
  - URL 正規化、SSRF 対策、XML 攻撃対策（defusedxml）、冪等保存
- ニュース NLP（OpenAI を用いたセンチメント評価）
  - 銘柄単位のバッチスコアリング（gpt-4o-mini、JSON mode）、リトライ・バリデーション
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次で 'bull'/'neutral'/'bear' 判定
- ファクター計算・研究ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC（Spearman）、統計サマリー、z-score 正規化
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の階層で監査テーブルを初期化・管理
- J-Quants API クライアント
  - レート制御、認証トークンの自動リフレッシュ、ページネーション対応、DuckDB 保存用ユーティリティ

---

## セットアップ

前提
- Python 3.10+（型表記に | 演算子、typing の近代機能を使用）
- Git / 任意の仮想環境

推奨パッケージ（例）
- duckdb
- openai
- defusedxml

例: 仮想環境作成とインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# パッケージが pip 配布されている場合:
# pip install -e .
```

環境変数（.env）
- 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくファイル位置で探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 主要な環境変数（README 用抜粋）:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに必要）
  - KABU_API_PASSWORD: kabu API のパスワード（実行系が使う場合）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 環境 (development | paper_trading | live)
  - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知関連（任意）
  - PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス（任意）

簡単な .env.example（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト上での簡単な利用例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続を作成して日次 ETL を実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを生成（ai/news_nlp.py）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定（ai/regime_detector.py）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（audit schema）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

5) 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとのファクター辞書リスト
```

注意点
- LLM（OpenAI）を呼ぶ関数は API キー（OPENAI_API_KEY）を必要とします。未設定時は ValueError を送出します。
- J-Quants API 呼び出しはレート制御・リトライ・401 リフレッシュを内蔵しています。JQUANTS_REFRESH_TOKEN は必須です。
- ETL / API 呼び出しはネットワークアクセスを伴います。CI / テストでは該当関数をモックしてください。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主な構成（src/kabusys 配下）です。実際のファイル数はこの一覧以外にも存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                             -- 環境変数と Settings 管理（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py                          -- ニュースセンチメントスコア（LLM 呼び出し）
    - regime_detector.py                   -- 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py                    -- J-Quants API クライアント（取得/保存ユーティリティ）
    - pipeline.py                          -- ETL パイプライン（run_daily_etl 等）
    - etl.py                               -- ETLResult の公開 API
    - news_collector.py                    -- RSS 収集 / 前処理 / 保存
    - calendar_management.py               -- 市場カレンダー管理・営業日ロジック
    - quality.py                           -- データ品質チェック（QualityIssue）
    - stats.py                             -- zscore_normalize 等
    - audit.py                             -- 監査ログテーブル初期化・管理
  - research/
    - __init__.py
    - factor_research.py                   -- Momentum/Value/Volatility 等の計算
    - feature_exploration.py               -- forward returns, IC, factor summary
  - ai/, data/, research/ はそれぞれテスト可能な単位関数で設計されています。

---

## 実装上の注意点 / 設計メモ

- ルックアヘッドバイアス防止:
  - 日付関連の内部関数は基本的に date.today()/datetime.today() を直接参照せず、呼び出し側で target_date を渡す設計です（バッチ再現性確保）。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を活用して冪等保存を実現しています。
- フェイルセーフ:
  - LLM 呼出し失敗時はフォールバックスコア（0.0）で継続するなど、致命的例外としない設計箇所があります。
- セキュリティ:
  - news_collector では SSRF 対策（ホストの private 判定、リダイレクト検査）、XML パースに defusedxml を使用しています。
- レート制御:
  - J-Quants クライアントは 120 req/min の制限に合わせた固定間隔スロットリングを実装しています。

---

## 付記

- 本リポジトリは運用・研究用途を想定したユーティリティ群です。実際に発注やリアルマネーで運用する前に、十分な統合テスト・リスク管理を行ってください。
- ログ出力・監視・ジョブスケジューリング（cron / systemd / Airflow 等）は利用環境に合わせて実装してください。

もし README に追記したいサンプルスクリプト、CI 設定例、Docker イメージ、または他の詳細（関数の API ドキュメント化やユニットテスト方針）があれば教えてください。必要に応じて追補します。