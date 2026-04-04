# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants / RSS / OpenAI を組み合わせて、データ収集（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（.env）
- 使い方（簡単なコード例）
- よくある操作
- ディレクトリ構成（主要ファイルの説明）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データプラットフォーム用のモジュール群です。主に以下の目的で設計されています。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS によるニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄単位・マクロ）評価
- ETF とニュースを合成した市場レジーム判定（bull/neutral/bear）
- 研究用途のファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → executions）用スキーマ初期化・管理

設計上の特徴として、ルックアヘッドバイアス（バックテストで未来情報を参照してしまうバイアス）を避けるために日時参照やクエリ条件に注意した実装方針が取られています。

---

## 機能一覧

主な機能（モジュール単位）
- kabusys.data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存関数）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（RSS パーサ、前処理、SSRF ガード）
  - データ品質チェック（missing/spike/duplicates/date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - ニュースNLP（score_news：銘柄毎の ai_score を ai_scores テーブルへ書き込み）
  - 市場レジーム判定（score_regime：ETF 1321 の MA とマクロニュースを合成）
- kabusys.research
  - ファクター計算（momentum/value/volatility 等）
  - 特徴量探索・IC 計算・統計サマリー
- kabusys.config
  - 環境変数および .env 自動ロード（プロジェクトルート検出）
- 監視・実行に必要な設定（PID / KILL フラグファイル等）やログレベル管理

---

## 前提条件

- Python 3.10+
- 必要パッケージ（最低限、例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants、RSS、OpenAI など）

※ 実際のバージョンや追加依存はプロジェクトの requirements.txt / pyproject.toml を参照してください（このリポジトリのスニペットには requirements ファイルは含まれていません）。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクト配布に合わせ pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して依存をインストール
3. 環境変数を設定（.env をプロジェクトルートに置くのが推奨）
4. DuckDB データベースパス等のファイルパスにアクセス可能なディレクトリを作成

自動 .env ロードの挙動:
- 自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。
- 読み込み順（優先度）: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。

---

## 環境変数（例）

主要な環境変数（.env に記載する想定）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabu API のパスワード（取引実行を使う場合）
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（任意）
- DUCKDB_PATH            : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite パス（監視 DB 等）
- PID_FILE_PATH, KILL_FLAG_PATH など監視用パス
- KABUSYS_ENV            : 実行モード ("development" / "paper_trading" / "live")
- LOG_LEVEL              : ログレベル ("DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL")

.example（.env.example を作る場合の一例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=~/.kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

重要: API キーやトークンは決してバージョン管理にコミットしないでください。

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- ETL（日次パイプライン）の実行例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today(), run_quality_checks=True)
print(result.to_dict())
```

- ニュースセンチメント（銘柄単位）を生成:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# これで監査テーブルが作成されます
```

- 研究用ファクター計算、統計ユーティリティ:
```python
from kabusys.research import calc_momentum, calc_value
from kabusys.data.stats import zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- score_news / score_regime は OpenAI API キー（api_key 引数 or OPENAI_API_KEY 環境変数）が必要です。
- 各関数はルックアヘッドバイアス対策のため target_date を外部から与える設計になっており、内部で date.today() を参照しない箇所が多くあります（バックテストに適しています）。

---

## よくある操作

- 自動 .env ロードを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

- ログレベル変更:
  - LOG_LEVEL 環境変数で指定（例: LOG_LEVEL=DEBUG）。

- DuckDB ファイル場所変更:
  - DUCKDB_PATH 環境変数を設定（例: DUCKDB_PATH=/path/to/kabusys.duckdb）。

- OpenAI 呼び出しのテスト:
  - 実際の API 呼び出しを避けるため unittest.mock.patch で _call_openai_api を差し替えられるよう実装されています（単体テスト向け）。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ初期化。公開サブパッケージを定義。
- config.py
  - 環境変数読み込み（.env/.env.local）、Settings クラス（設定アクセス）。
- ai/
  - __init__.py
  - news_nlp.py: ニュースを対象に銘柄ごとのセンチメントを生成し ai_scores に書き込む処理。
  - regime_detector.py: ETF 1321 の MA200 乖離とニュースのマクロセンチメントを合成して market_regime に書き込む。
- data/
  - __init__.py
  - jquants_client.py: J-Quants API の取得・保存ロジック（レートリミット、リトライ、トークンリフレッシュ、DuckDB への保存）。
  - pipeline.py: ETL（run_daily_etl 等）と ETLResult 定義。
  - calendar_management.py: 市場カレンダーの管理・営業日判定・カレンダー更新ジョブ。
  - news_collector.py: RSS 取得、前処理、SSRF 対策、raw_news への保存ロジック（説明書きあり）。
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付不整合）。
  - stats.py: zscore_normalize などの統計ユーティリティ。
  - audit.py: 監査ログテーブルの DDL と初期化（init_audit_schema / init_audit_db）。
  - etl.py: ETLResult のエクスポート。
- research/
  - __init__.py
  - factor_research.py: momentum/value/volatility ファクター計算。
  - feature_exploration.py: forward returns / IC / rank / factor_summary 等。
- その他:
  - monitoring, execution, strategy などのパッケージがパッケージ一覧に含まれていますが、ここに示したコードスニペットは上記モジュールが中心です。

---

## 注意事項

- 実際の取引を行う場合は、kabu API や注文ロジックの安全性・金額管理・二重発注防止、法令遵守を十分に確認してください。本ライブラリは研究・運用補助を目的とした基盤であり、責任ある運用が前提です。
- API キーやトークンは機密情報です。環境変数やシークレット管理ソリューションを利用し、リポジトリにコミットしないでください。
- OpenAI / J-Quants / kabu API の利用には各サービスの利用規約・レート制限があります。実運用ではレート制限や料金に注意してください。
- DuckDB に対する executemany の空パラメータ等、バージョン依存の挙動に配慮した実装がされていますが、DuckDB のバージョン差異により挙動が異なる場合があります。

---

追加で README に記載したい例や、具体的な実行スクリプト（cron / systemd 用）・CI 設定・requirements ファイルの雛形などがあればお知らせください。必要に応じて追記します。