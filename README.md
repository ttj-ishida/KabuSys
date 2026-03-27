# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリです。  
DuckDB をデータ基盤に、J-Quants や RSS・OpenAI（gpt-4o-mini）を活用してデータ収集・品質チェック・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ機能を提供します。

---

## 主な特徴（機能一覧）

- 環境変数 / .env ベースの設定管理（自動ロード）
- J-Quants API クライアント（差分取得・ページネーション・トークン自動更新・レート制御・リトライ）
- ETL パイプライン（価格、財務、マーケットカレンダーの差分取得・保存・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- ニュース収集（RSS -> raw_news、SSRF/サイズ/トラッキング除去対策）
- ニュース NLP（OpenAI を用いた銘柄別センチメント集約・バッチ処理・結果の検証・ai_scores への保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 研究用ユーティリティ（モメンタム/ボラティリティ/バリュー等のファクター、将来リターン、IC、統計サマリ、Z スコア正規化）
- 監査ログ（signal / order_request / executions テーブル、冪等化・時刻は UTC）
- DuckDB 向けの冪等保存ロジック（ON CONFLICT DO UPDATE）を実装

---

## 必要環境・依存ライブラリ

最低限の依存（抜粋）：
- Python 3.10+
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt に他の依存が定義される想定です）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # 開発環境であれば pip install -e .
   ```

4. 環境変数設定
   プロジェクトルートに `.env`（および任意で `.env.local`）を作成すると、自動で読み込まれます。
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨される `.env` の例（`.env.example` を参考に作成してください）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxx

   # OpenAI
   OPENAI_API_KEY=sk-xxxx

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（監視通知等を利用する場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境 / ログ
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API と実行例）

以下は Python API を直接利用する例です。CLI は本コードベースには含まれていません（必要に応じてラッパーを作成してください）。

- DuckDB 接続の作成（設定値を利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダー・価格・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP（ai_scores への書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"written: {written}")
  ```

- 市場レジームスコア算出（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 研究用：ファクター計算 / 特徴量解析
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  from datetime import date

  target = date(2026,3,20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  fwd = calc_forward_returns(conn, target)
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- 監査ログ（audit）スキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db

  # :memory: でインメモリ DB、またはファイルパス
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 設定アクセス例
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live)
  ```

---

## 重要な挙動・注意点

- 設定自動ロード
  - パッケージ内の config はプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
  - 読み込み順序: OS 環境変数 > .env.local > .env

- Look-ahead bias の防止
  - すべての ETL / スコアリング関数は内部で datetime.today() を直接参照しないか、明確に target_date を受け取る設計です。バックテスト用途に配慮しています。

- J-Quants クライアント
  - レート制御（120 req/min）とリトライ（408/429/5xx に対する指数バックオフ）、401 の場合はリフレッシュトークンを用いた自動再取得を実装しています。
  - 保存時は DuckDB に対して冪等な INSERT ... ON CONFLICT DO UPDATE を使用します。

- OpenAI 呼び出し
  - news_nlp と regime_detector は gpt-4o-mini を想定した JSON Mode を使用します。API エラー時はフォールバックや部分スキップのロジックがあります（全体を落とさない設計）。
  - テスト時は内部の _call_openai_api をモックする想定です。

- ニュース収集（RSS）
  - SSRF 対策（リダイレクト検査、プライベート IP 検査）、受信サイズ上限、トラッキングパラメータ除去、XML の安全パーサ（defusedxml）を採用しています。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（銘柄別センチメント）
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL の公開型再エクスポート（ETLResult）
    - calendar_management.py     — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py          — RSS ニュース収集
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー 等

---

## 開発・テストのヒント

- OpenAI や外部 API 呼び出しはモックしやすいように内部関数（例: _call_openai_api）を分離しています。ユニットテストではこれらを patch してください。
- ETL の品質チェックは Fail-Fast ではなく問題を集める設計です。ETLResult の `quality_issues` を参照して運用ルールに従ってください。
- DuckDB の executemany に関する制約（空リスト不可）や型互換性に配慮した実装があります。実際の DB マイグレーションやスキーマ初期化時は注意してください。

---

何か特定の機能の使い方（例: news_nlp のプロンプト調整、J-Quants 呼び出しのテスト方法、監査ログスキーマ拡張）について詳しく知りたい場合は教えてください。README をより運用向けに拡張することもできます。