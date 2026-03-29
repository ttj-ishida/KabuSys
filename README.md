# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（オーダー/約定トレース）などを含むモジュール群を提供します。

主な設計方針：
- バックテストにおけるルックアヘッドバイアスを意識した実装（date/times の扱いに注意）
- DuckDB を用いたローカルデータ格納と冪等保存（ON CONFLICT / INSERT … DO UPDATE）
- 外部 API 呼び出しはリトライ・レート制御を備えフェイルセーフに設計
- モジュールごとに再利用可能な関数群を提供（ETL / 研究 / AI / データ品質 / 監査）

---

## 機能一覧

- data/
  - ETL pipeline（J-Quants からの差分取得、保存、品質チェック）
  - market calendar 管理、営業日判定ユーティリティ
  - news_collector：RSS 収集、SSRF 対策、前処理、raw_news への保存
  - jquants_client：J-Quants API 呼び出し（認証、ページネーション、保存関数）
  - quality：データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit：戦略→シグナル→発注→約定の監査テーブル初期化・DB 初期化ユーティリティ
  - stats：Zスコア正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news：ニュース記事を LLM（gpt-4o-mini）で銘柄ごとにセンチメント化して `ai_scores` に保存
  - regime_detector.score_regime：ETF（1321）MA200乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定・保存
- research/
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration：将来リターン、IC（Information Coefficient）、統計サマリー等
- config：環境変数管理（.env 自動読み込み、必須チェック）

主な特徴：
- Look-ahead バイアス対策（内部で date.today() を盲目的に使わない設計）
- 冪等な DB 操作（ETL / 保存関数）
- API 呼び出しに対するリトライ・レート制御・トークン自動リフレッシュ（J-Quants）
- ニュース収集での SSRF / XML Bomb 対策（defusedxml、ホストチェック、サイズ制限）

---

## 前提環境 / 依存パッケージ（例）

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際のプロジェクトではさらに slack 連携等の依存がある可能性があります。requirements.txt を用意している場合はそれを利用してください。）

インストール例（仮）:
```
python -m pip install duckdb openai defusedxml
# 追加で必要なら:
# pip install slack_sdk
```

パッケージ開発環境でのインストール（リポジトリルートで）:
```
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動

2. Python 仮想環境を作成して依存関係をインストール

3. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）
   - 自動ロードはデフォルトで有効。無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN: Slack 通知用（必要な場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携がある場合）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 .env（プロジェクトルート、.env.example を参考に作成）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-....
SLACK_BOT_TOKEN=xoxb-....
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- config.Settings は自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。
- `.env.local` は `.env` の上書き（override=True）として扱われます。

---

## 使い方（主要なユースケース）

以下は最小限の Python からの呼び出し例です。実運用ではログ設定・例外処理等を適切に行ってください。

1) DuckDB 接続を作成して ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成して ai_scores に保存
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", written)
```

3) 市場レジーム判定（ETF 1321 MA + マクロニュース）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査用 DuckDB の初期化（発注・約定の監査テーブル）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリを自動作成
# 以降 conn を使って監査テーブルに書き込みが可能
```

5) 研究用ユーティリティ（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
norm = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 実装上の注意点 / 運用メモ

- ニュース NLP / レジーム判定は OpenAI（gpt-4o-mini）を使用する想定。API レスポンスのパース失敗や API エラー時にはフェイルセーフ（スコア 0.0 等）で継続する設計です。
- J-Quants API 呼び出しは内部で 120 req/min のレート制限を守る実装と、401 時のトークン自動リフレッシュを備えています。
- ETL は各ステップで個別に例外をハンドリングし、1 ステップの失敗で全体が止まらないようにしています。結果は ETLResult に集約されます。
- データ品質チェック（quality.run_all_checks）は ETL 後の診断用で、検出された問題は QualityIssue のリストで返ります。重大度（error/warning）を見て運用側で対応してください。
- calendar / trading day ヘルパーは market_calendar テーブルが存在する場合は DB を優先、それが無い場合は土日ベースのフォールバックを行います。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なモジュール構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETL result export)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - audit.py
    - stats.py
    - (その他 jquants_client に紐づく保存・取得ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他）...
  - ai/（LLM 関連）
  - monitoring/（README の冒頭で __all__ に入るが実装に依存）

この README はコード内の docstring と設計コメントを元に作成しています。各モジュールの docstring に詳しい挙動や設計方針が記載されていますので、実装の詳細は該当ファイルを参照してください。

---

必要であれば、README に以下を追加できます：
- CI / テスト実行方法（pytest 等）
- 開発者向けのコーディング規約や型チェック（mypy）設定
- 具体的な SQL スキーマ定義（raw_* / ai_scores / market_calendar 等）
ご希望があれば追記します。