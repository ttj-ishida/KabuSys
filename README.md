# KabuSys

日本株の自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants からの差分取得）、データ品質チェック、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含むモジュール群を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（.env）
- ディレクトリ構成
- テスト・開発メモ

---

## プロジェクト概要

KabuSys は、日本株の自動売買システム向けにデータ取得・前処理・解析・監査までをカバーする内部ライブラリ群です。主な役割は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL。
- raw_prices（raw_prices）に対する品質チェック（欠損・スパイク・重複・日付不整合）。
- RSS ベースのニュース収集と、OpenAI を使った銘柄別ニュースセンチメント（ai_scores）算出。
- ETF の MA 乖離＋マクロニュースの LLM 評価を合成した市場レジーム判定（bull/neutral/bear）。
- ファクター生成（モメンタム・バリュー・ボラティリティ）および研究用ユーティリティ。
- 発注→約定の監査（audit）テーブル定義と初期化ユーティリティ。
- セットアップや実行を容易にする設定管理モジュール（.env の自動読み込み等）。

設計方針としては「ルックアヘッドバイアスを避ける」「失敗時はフォールバックして継続する（フェイルセーフ）」「DuckDB を中心とした冪等操作」を重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート判定）
  - settings オブジェクト（J-Quants トークン、DB パス、Slack トークン等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・リトライ・保存ロジック）
  - pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（missing, spike, duplicates, date consistency）
  - news_collector: RSS 取得・前処理・SSRF 対策
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - audit: 監査テーブル DDL / 初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize などの統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でバッチ評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離 と マクロニュース LLM を合成して market_regime に書き込む

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

設計上の注意点（抜粋）:
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢性を重視。
- ニュース収集は URL 正規化・トラッキング除去・SSRF 対策などを実装。
- ETL は差分更新・バックフィル（データ修正吸収）を行う。
- DuckDB を使った idempotent な保存（ON CONFLICT / executemany の扱いに注意）。

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで | を使用）
- システムに DuckDB がインストールされていれば duckdb Python パッケージを使います。

推奨手順（例）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows

3. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトで追加の依存があれば requirements.txt を作成して pip install -r requirements.txt）

4. .env を作成（プロジェクトルート）
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと、自動で読み込まれます。
   自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ作成（デフォルト DB パス使用時）
   mkdir -p data

---

## 環境変数（.env） — 主なキー

README では重要な環境変数と用途を示します。プロジェクトルートに .env を置くと自動読み込みされます（ただし既存の OS 環境変数は上書きされません）。

必須（本番的に必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector が参照）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution モジュールで使用）
- SLACK_BOT_TOKEN: Slack 通知に用いる Bot トークン（monitoring 等）
- SLACK_CHANNEL_ID: Slack の通知先チャンネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / ...)

注意: config.Settings は必須キーが未設定の場合に ValueError を投げます。

---

## 使い方（例）

以下は典型的な利用例（Python スクリプト内での呼び出し例）。

1) ETL（日次パイプライン）の実行例

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB へ接続（settings.duckdb_path は Path オブジェクト）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI API キーは OPENAI_API_KEY または api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

3) 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査用の DuckDB を作る）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 既定の settings.duckdb_path に作成する例
conn = init_audit_db(settings.duckdb_path)
# conn を使って監査テーブルを参照・利用できます
```

5) 研究用ファクター計算（例：モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# レコードは list[dict] 形式（date, code, mom_1m, mom_3m, ...）
```

注意点:
- OpenAI 呼び出しはネットワークエラーや API 制限に備えたリトライを行いますが、テスト時は関数内部の _call_openai_api をモックしてテストしてください（コード内コメントあり）。
- run_daily_etl の target_date 省略時は当日（date.today()）ですが、内部アルゴリズムは「ルックアヘッドバイアス」を避ける設計になっています。

---

## ディレクトリ構成（主要ファイル／モジュール）

（src/kabusys 以下）

- __init__.py
  - パッケージエクスポート。version 等。

- config.py
  - .env 自動読み込み、Settings（各種設定取得）を提供。

- ai/
  - __init__.py
  - news_nlp.py: ニュースの集約・OpenAI によるスコアリング → ai_scores テーブルに保存
  - regime_detector.py: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime に保存

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py: ETL のメイン（run_daily_etl など）と ETLResult 定義
  - etl.py: ETLResult の再エクスポート
  - quality.py: データ品質チェック（QualityIssue 型）
  - stats.py: zscore_normalize 等
  - news_collector.py: RSS フィード取得、前処理、SSRF 対策
  - calendar_management.py: 市場カレンダーの管理、営業日判定、calendar_update_job
  - audit.py: 監査ログ（DDL / 初期化ユーティリティ）
  - pipeline.py (上記) -> ETL 実装・ユーティリティ

- research/
  - __init__.py
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank

- ai, data, research の各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受けて処理を行う設計になっています。

---

## テスト・開発メモ

- OpenAI 呼び出しやネットワーク依存部分はユニットテストでモックする設計になっています（news_nlp._call_openai_api や regime_detector._call_openai_api など）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）を基に動作します。CI やテストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への executemany に空リストを渡すと問題になるバージョンがあるため、コード内で空チェックを行っています（互換性を確保）。
- ニュース収集は defusedxml を利用して XML 関連の攻撃から保護しています。

---

以上が README の概要です。必要があれば以下の追加情報も作成できます：
- .env.example（テンプレート）
- requirements.txt / poetry pyproject.toml 例
- CLI スクリプト（ETL を定期実行するためのサンプル）
- 運用手順（cron / systemd / コンテナ化例）

どれを追加しましょうか？