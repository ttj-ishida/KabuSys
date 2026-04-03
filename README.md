# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データのETL、ニュースNLP・市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）など、アルゴリズムトレーディングに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を持つモジュール群です：

- J-Quants API を用いた市場データ・財務データ・カレンダーの取得と DuckDB への保存（差分取得・冪等保存）
- RSS ベースのニュース収集と前処理（raw_news / news_symbols テーブル）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（ai_scores テーブルへの保存）
- マクロセンチメントとETF（1321）の MA 乖離を組み合わせた市場レジーム判定（market_regime テーブル）
- ファクター計算（モメンタム、ボラティリティ、バリューなど）および特徴量探索（IC 計算等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
- 環境設定管理（.env 自動読込、設定クラス）

設計方針のポイント：
- ルックアヘッドバイアス回避（内部で datetime.today() 等を不用意に参照しない）
- DuckDB と SQL を中心に効率的に処理
- 冪等性・フェイルセーフ重視（部分失敗時の保護、API リトライなど）
- 外部トークンや API キーを環境変数で管理

---

## 機能一覧

主な公開 API / 機能（モジュール別）

- kabusys.config
  - settings: 環境変数からアプリ設定を取得（JQUANTS_REFRESH_TOKEN 等）
  - 自動 .env 読込（プロジェクトルート検出、優先順位: OS 環境 > .env.local > .env）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能

- kabusys.data
  - jquants_client: J-Quants API 呼び出し、取得・保存関数（fetch_*, save_*）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL のエントリ）
  - news_collector: RSS 取得・前処理・raw_news への保存支援ユーティリティ
  - calendar_management: 営業日判定（is_trading_day / next_trading_day 等）、calendar_update_job
  - quality: データ品質チェック（missing_data / spike / duplicates / date_consistency）
  - audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを LLM で解析し ai_scores を更新
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジーム（bull/neutral/bear）を判定して market_regime に書き込む

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を利用した正規化処理

---

## 必須環境 / 依存

最低限の Python バージョン: 3.10+（PEP604 の union 型表記などを使用）

必須パッケージ（一例）:
- duckdb
- openai
- defusedxml

（プロジェクトの pyproject.toml / requirements.txt に依存関係を記載してください）

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数です。実運用では .env（または .env.local）を用意してください。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token 等で使用。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（発注系を実装する際に使用）。

- KABU_API_BASE_URL (任意)  
  kabuステーション API のベース URL。デフォルト: http://localhost:18080/kabusapi

- OPENAI_API_KEY (必須 for AI 機能)  
  OpenAI API 呼び出しに使用。score_news / score_regime にも指定可能（関数引数で上書き可）。

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意)  
  LINE 通知設定（未使用の箇所がある場合は空文字可）。

- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  監視系 DB 用デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  有効値: development, paper_trading, live（デフォルト development）

- LOG_LEVEL (任意)  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  
  パッケージインポート時の自動 .env ロードを無効にします（テスト時に便利）。

.env の自動読み込みについて:
- プロジェクトルートは __file__ の親階層から `.git` または `pyproject.toml` を探索して決定します。
- 読み込み優先度: OS 環境 > .env.local > .env
- .env ロードは存在しなければ無視され、安全側の挙動です。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   例（pip）:
   - pip install -U pip
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements ファイルがあればそれを使用してください。

4. パッケージを開発モードでインストール（ソースに setup / pyproject がある場合）
   - pip install -e .

5. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数として設定してください。
   - 最小例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

6. DuckDB / 監査 DB の初期化（必要に応じて）
   - 監査ログ専用 DB を初期化する例（Python スクリプト）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - 既存のデータベースに監査スキーマを追加する:
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)

---

## 使い方（サンプル）

以下に典型的な利用フローの Python サンプルを示します。

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定を実行して market_regime に保存する:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（別 DB として）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# init_audit_db は初期化済みの duckdb 接続を返します
```

- ファクター計算 / 研究用ユーティリティ例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

注意点:
- score_news / score_regime は OpenAI API キーを必要とします。api_key を関数引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- jquants_client の fetch 関数は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）を必要とします。

---

## ディレクトリ構成（概要）

以下は主要なファイル・モジュールの構成（src/kabusys 以下）です。サブモジュールごとに役割を併記します。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/設定管理（.env 自動読込）
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュース NLP（score_news）
      - regime_detector.py           — 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（fetch/save 関数）
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - etl.py                       — ETL 結果クラス再エクスポート
      - calendar_management.py       — マーケットカレンダー管理・営業日ロジック
      - news_collector.py            — RSS 取得・前処理ユーティリティ
      - quality.py                   — データ品質チェック
      - stats.py                     — 統計ユーティリティ（zscore_normalize）
      - audit.py                     — 監査ログテーブル定義と初期化
    - research/
      - __init__.py
      - factor_research.py           — ファクター計算（momentum/value/volatility）
      - feature_exploration.py       — 将来リターン、IC、統計サマリ等
    - research/...                    — その他研究用ユーティリティ
    - (その他戦略/実行/監視モジュールが追加される想定)

---

## 開発・運用に関する注意事項

- 環境設定は安全に管理してください（API トークンを公開リポジトリに置かない）。
- OpenAI API 呼び出しはコストとレート制限に注意してください。コード内でもリトライ制御・バッチ処理を行っていますが、実際の運用では上限やコスト管理を設計してください。
- J-Quants の API レート制限や認証は仕様に従ってください。jquants_client にはレート制御・リトライ・トークンリフレッシュの実装があります。
- DuckDB の SQL 実行は大きなデータに対して高速ですが、メモリ・I/O を監視してください。

---

## 追加情報 / 参考

- 自動 .env ロードはプロジェクトルートを `.git` または `pyproject.toml` で検出します。CI やテストで環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 各モジュールの詳細な振る舞い（例: リトライロジック、ウィンドウ定義、スコア合成の重みなど）は各ソースファイルのドキュメンテーションストリング（docstring）に記載されています。実装の微妙な挙動を確認したい場合は該当ファイルを参照してください。

---

この README はコードベースの主な使い方・構造をまとめたものです。必要に応じて README を拡張して運用手順（デプロイ、cron / バッチ設定、監視の具体的な手順）や API キーの取得方法、サンプル .env.example を追記してください。