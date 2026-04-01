# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP による銘柄センチメント評価、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注・約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株運用のためのデータ取得・品質管理・AI スコアリング・リサーチ・監査ログを一貫して扱うためのモジュール群です。主な設計方針は以下の通りです。

- Look-ahead bias を避ける（内部で datetime.now()/date.today() を直接使わない、明示的な target_date を使う）
- DuckDB を使ったローカルデータレイク（冪等保存、ON CONFLICT 処理）
- J-Quants API の安全な呼び出し（レート制御・リトライ・トークン自動更新）
- OpenAI（gpt-4o-mini）の JSON mode を利用したニュースセンチメント評価（フェイルセーフ）
- ニュース収集の SSRF 防御・XML パース防御
- 監査ログによるシグナル→発注→約定の完全トレーサビリティ

---

## 機能一覧

- data
  - jquants_client: J-Quants API から株価/財務/カレンダー等の取得、DuckDB への保存（save_* 系）
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS から記事取得、前処理、raw_news 保存（SSRF対策・トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク・重複・将来日付等）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化・DB 作成
  - stats: 共通統計関数（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI に投げて ai_scores へ書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定
- research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリ等
- config: 環境変数の読み込み（.env/.env.local の自動読込、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化）、Settings オブジェクト

---

## セットアップ

この README はコードベースから推測した最小限のセットアップ手順を示します。実際はプロジェクトの pyproject.toml / requirements.txt を参照してください。

前提
- Python 3.10+ を推奨（型ヒントに union 型などを利用）
- DuckDB、OpenAI SDK、defusedxml 等が必要

推奨インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. （任意）プロジェクトを editable install
   - pip install -e .

requirements.txt の一例（必要に応じ追記）
- duckdb
- openai
- defusedxml

環境変数 / .env ファイル
- リポジトリルートの .env/.env.local を自動で読み込みます（CWD ではなくパッケージ位置から .git / pyproject.toml を探索）。
- 自動読込を抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/..（デフォルト INFO）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.score_news / regime_detector）

例: .env (最小)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は主要な関数の利用例です。実行時は適切な環境変数を設定し、DuckDB のスキーマや必要テーブルを用意してください。

1) 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None で環境変数 OPENAI_API_KEY を使用
print(f"wrote {n_written} scores")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: でも可
```

5) 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は list[dict] 形式
```

注意点
- OpenAI の呼び出しはネットワークの失敗や API レート制限に対しフェイルセーフ（スコア 0.0）・リトライを行う設計です。ただし API キーは必須です。
- ETL/保存処理は DuckDB 側のスキーマが前提です。schema 初期化やマイグレーションは別途用意してください。
- テスト時は内部の外部呼び出し（OpenAI / urllib / _urlopen など）をモックすることを想定した設計です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - etl.py
  - news_collector.py
  - quality.py
  - calendar_management.py
  - stats.py
  - audit.py
  - (その他: e.g. pipeline ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring / execution / strategy 等はパッケージの __all__ に名前はあるが、本リストは主に data/ai/research に焦点を当てています。

各モジュールの役割（要約）
- config.py: 環境変数の解析・自動読み込み・Settings 提供
- data/jquants_client.py: J-Quants API の取得と DuckDB 保存（fetch_*/save_*）
- data/pipeline.py: ETL の orchestration（run_daily_etl 等）
- data/news_collector.py: RSS 収集と前処理（SSRF/パラメータ正規化）
- data/quality.py: データ品質チェック
- data/calendar_management.py: 営業日判定・カレンダー更新ジョブ
- ai/news_nlp.py: 銘柄ごとのニュースセンチメント算出（OpenAI）
- ai/regime_detector.py: MA200 とマクロニュースを合成して市場レジーム判定
- research/*: ファクター計算と分析ユーティリティ

---

## 運用上の注意 / ベストプラクティス

- 環境分離: `KABUSYS_ENV` を development / paper_trading / live で分け、実際の発注や機密情報の扱いに注意してください。
- シークレット管理: OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN などは安全な方法で管理する（Vault / CI secrets 等）。.env はローカル開発用に限定してください。
- DB バックアップ: DuckDB ファイルは定期的にバックアップしてください。
- テスト: OpenAI 呼び出しやネットワーク部分はモック可能な設計です。ユニットテストでは該当箇所を差し替えてください。
- スキーマ: audit / raw_prices / raw_news 等のテーブルスキーマはコードのコメント/DDL を参照して初期化してください（audit.init_audit_schema などを使用）。

---

README はここまでです。追加で「インストール用の setup/pyproject のひな形」や「テーブルスキーマの初期化スクリプト」や「具体的な運用手順（cron ジョブ例 / systemd unit）」などを作成希望であれば教えてください。