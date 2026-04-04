# KabuSys

日本株向けのデータプラットフォーム兼自動売買研究フレームワーク。J-Quants / JPX / RSS / OpenAI 等からデータを収集・品質チェック・加工し、研究（ファクター算出・特徴量分析）、AI ニュースセンチメント評価、マーケットレジーム判定、監査ログ（発注〜約定トレーサビリティ）などの機能を提供します。

---

## 特徴（概要）

- J-Quants API を用いた差分 ETL（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたローカルデータ格納・クエリ
- ニュース収集（RSS）・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位）とマクロセンチメントを合成した市場レジーム判定
- 研究モジュール：モメンタム / ボラティリティ / バリュー等のファクター算出、将来リターン、IC、統計サマリ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）用スキーマ初期化ユーティリティ
- 環境変数・.env 自動読み込み（プロジェクトルート検出）と設定ラッパー

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からの取得（daily_quotes / financial_statements / trading_calendar / listed_info）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - トークン自動リフレッシュ / レートリミッタ / リトライ
- data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を ETLResult で返却、品質チェック実行
- data.news_collector
  - RSS フィード取得、安全対策（SSRF・サイズ上限・XML 漏洩対策）
  - 記事正規化・ID 生成（URL 正規化 -> SHA256 トランケート）
- ai.news_nlp
  - ニュース記事をまとめて OpenAI に投げ、各銘柄の ai_score を ai_scores テーブルへ書き込み
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離 + マクロセンチメントを合成して market_regime を日次で判定
- research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data.audit
  - 監査スキーマ初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子や型注釈の利用に対応）
- Git, インターネットアクセス（API 連係のため）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合はそれを使ってください）
   - 開発時は linters / test ライブラリ等を追加でインストールしてください。

4. データ用ディレクトリ作成（設定でパスを変更可能）
   - デフォルト DB パス等は以下（settings 参照）
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視用): data/monitoring.db
     - PID / kill フラグ: data/execution.pid, data/kill.flag
   - 例:
     - mkdir -p data

5. 環境変数設定
   - .env または OS 環境変数を利用します。プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます。
   - 主要な環境変数（最小限）
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabu API パスワード（発注系を利用する場合）
     - OPENAI_API_KEY (必須: AI 機能を使う場合) — OpenAI API キー
   - 任意/その他
     - KABUSYS_ENV (development|paper_trading|live) — 動作モード（デフォルト development）
     - LOG_LEVEL (DEBUG|INFO|...) — ログレベル
     - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化可能（テスト時など）

例 .env（テンプレート）
    JQUANTS_REFRESH_TOKEN=xxxxxxxx
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（基本例）

すべての関数はプログラムから直接呼び出して利用できます。以下は代表的なユースケースの例です。

- DuckDB 接続の作成例

```python
import duckdb
from kabusys.config import settings

# ファイル DB を使う場合
conn = duckdb.connect(str(settings.duckdb_path))

# インメモリでテストする場合
# conn = duckdb.connect(":memory:")
```

- 日次 ETL 実行例

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント評価（ai.news_nlp.score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API Key は環境変数 OPENAI_API_KEY または api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 03, 20), api_key=None)
```

- 監査データベース初期化（監査テーブル作成）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成
# これで signal_events / order_requests / executions のテーブルが作成されます
```

- データ品質チェックの実行

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意点:
- AI を呼ぶ機能（score_news, score_regime）は OpenAI API キーが必要です（引数 api_key または環境変数 OPENAI_API_KEY）。
- ETL / 保存処理は冪等設計になっていますが、運用時はバックアップやトランザクションの理解を推奨します。
- 実運用（実際の発注）を行う場合は kabu ステーション API 周りの認証・安全確認を必ず行ってください（KABU_API_PASSWORD 等）。

---

## ディレクトリ構成（主要ファイルと概要）

プロジェクトの主要な配置（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 機構（.env 自動ロード、必須変数チェック）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとにまとめて OpenAI でセンチメント評価 -> ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA 乖離とマクロニュースで市場レジーム判定 -> market_regime に保存
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API の取得・保存用クライアント（レート制御・リトライ・トークン管理）
    - pipeline.py
      - run_daily_etl 等の日次 ETL パイプラインと ETLResult
    - calendar_management.py
      - market_calendar 周りのユーティリティ（営業日判定 / next/prev / calendar_update_job）
    - news_collector.py
      - RSS 収集・前処理・raw_news への保存ロジック（SSRF/サイズ対策）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査スキーマ定義と初期化ユーティリティ
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility（ファクター計算）
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank（研究補助関数）

（各ファイルの詳細なドキュメントはソース内の docstring を参照してください）

---

## 環境変数一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（ETL 実行に必須）
- 発注 / 実運用で必要
  - KABU_API_PASSWORD — kabu ステーション API パスワード
- AI 機能利用時
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime）
- 任意
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — ログレベル（INFO 等）
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

---

## その他の注意点 / ベストプラクティス

- Look-ahead バイアス対策
  - モジュール内の多くの関数は datetime.today() / date.today() を直接参照しない設計で、backtest 等での利便性を考慮しています。バックテストでは明示的に target_date を渡してください。
- DB マイグレーション・スキーマ
  - DuckDB のスキーマは実行時に作成するユーティリティや別途スキーマ初期化コードが必要です（audit.init_audit_schema など）。
- エラーハンドリング
  - 外部 API 呼び出しはリトライ・フェイルセーフ設計（多くのケースで失敗時はスキップして継続）になっています。運用ではログとアラート設定を行ってください。
- テスト
  - 環境変数自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を使うとテストが安定します。OpenAI / J-Quants 呼び出し部分はモック可能な設計になっています（内部の _call_openai_api 等を patch ）。

---

必要であれば、以下も作成できます：
- サンプル .env.example
- 実行用スクリプト（CLI）ラッパー
- requirements.txt / pyproject.toml 例
- データベーススキーマ初期化スクリプト

README の補足や具体的な実行例（CI / systemd / cron での運用スニペット）など、さらに欲しい内容があれば教えてください。