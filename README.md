# KabuSys

日本株自動売買 / データプラットフォーム用の Python モジュール群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、監視・実行等の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチ基盤として以下を目的に設計されています。

- J-Quants API からの株価 / 財務 / カレンダー等の差分 ETL
- RSS ニュース収集と OpenAI を使ったニュースセンチメント（銘柄別 ai_score）生成
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- 監査ログ（シグナル → 注文 → 約定）用テーブルの初期化・管理
- データ品質チェック・カレンダー管理・ニュース収集での SSRF 対策など運用面の堅牢性

設計上の留意点として、バックテスト等でのルックアヘッドバイアスを避けるため「target_date を明示する」「datetime.today()/date.today() を内部で参照しない」方針が採られています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl／run_prices_etl／run_financials_etl／run_calendar_etl）
  - J-Quants クライアント（API リトライ・トークン自動リフレッシュ・レート制御）
  - market_calendar 管理・営業日判定ユーティリティ
  - ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - 汎用統計（Zスコア正規化）
- ai/
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）で銘柄別にスコアリングして ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離 + マクロニュースセンチメントの合成による市場レジーム判定
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC 計算・統計サマリー
- config
  - 環境変数/.env 管理（自動ロード機能、必須パラメータチェック）

---

## 必要条件 / 依存パッケージ

- Python 3.10+
- 必須 Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

インストール例（仮に pip を用いる場合）:

```
python -m pip install "duckdb" "openai" "defusedxml"
# 開発時はパッケージを editable install
python -m pip install -e .
```

（プロジェクトのパッケージ管理に Poetry や pip-tools を使う場合は適宜 requirements を準備してください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（読み込み順: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings から参照）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY (news_nlp/regime_detector の呼び出しで使用。引数で override 可能)
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 監視・プロセス制御
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
- 動作モード / ログ
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

設定の例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_pass
OPENAI_API_KEY=sk-xxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、パッケージをインストール
   - python と依存パッケージを適切にインストール（上記参照）
   - editable インストール: `python -m pip install -e .`

2. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成して上記の必須変数を設定
   - または環境変数としてエクスポート

3. データベース用ディレクトリを作成（必要なら）
   - デフォルトの DUCKDB_PATH の親ディレクトリを作成：`mkdir -p data`

4. 監査DB（オプション）初期化
   - 監査用 DB を作る場合:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な呼び出し例）

以下は Python REPL / スクリプトから利用する基本例です。

- 共通: settings と DuckDB 接続取得

```python
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（J-Quants の認証トークンは settings が参照）

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）

```python
from kabusys.ai.news_nlp import score_news
n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査テーブル初期化（既存 DuckDB 接続に DDL を追加）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- ファクター計算 / リサーチ関連

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

注意: 上記関数は DB 上に必要なテーブル（raw_prices, prices_daily, raw_financials, raw_news, news_symbols など）が存在し、データが整備されていることを前提とします。

---

## 実運用 / 安全性に関する注意点

- OpenAI の呼び出しは API コスト・レイテンシを伴います。API キー管理とレート制御に注意してください。
- J-Quants API のリクエストはレート制限（120 req/min）に対応していますが、ID トークンや接続失敗に対するログ・監視を行ってください。
- finance/market データは Look-ahead バイアスを避けるために target_date 未満のデータしか参照しない設計が施されています。テストやバックテスト時は date パラメータを適切に与えてください。
- ニュース収集モジュールには SSRF 対策・受信サイズ制限がありますが、外部 RSS の追加時はソースを慎重に選んでください。
- KABUSYS_ENV を `live` に設定した際は発注・実行パスに注意し、paper_trading での十分な検証を行ってから移行してください。

---

## ディレクトリ構成（抜粋）

プロジェクトは `src/kabusys` 配下にモジュールを持ちます。主要ファイル・モジュールは次の通りです。

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / .env 自動ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py                  - ニュース NLP（score_news）
    - regime_detector.py           - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント & 保存関数
    - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
    - etl.py                       - ETL 型再エクスポート
    - news_collector.py            - RSS 取得・前処理・保存
    - calendar_management.py       - 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py                   - データ品質チェック
    - stats.py                     - 統計ユーティリティ（zscore_normalize）
    - audit.py                     - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           - モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py       - 将来リターン / IC / 統計サマリー

（上記は抜粋です。詳細は各モジュールの docstring を参照してください）

---

## 開発 / テスト

- 自動 .env ロードを無効化してユニットテストを実行したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してテストを行ってください。
- 各モジュールは外部 API 呼び出しを分離してあり、ユニットテストでは該当関数（例: news_nlp._call_openai_api）をモックして振る舞いを検証できます。

---

README に含めきれない実装の詳細や運用手順は各モジュールの docstring（コード内コメント）に詳細が記載されています。必要であれば特定機能の使い方や実行スクリプト例を追加で作成しますので、どの機能のドキュメントが欲しいか教えてください。