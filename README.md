# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買（監査・ETL・シグナル生成・約定トレーサビリティ）を目的とした Python ライブラリです。本リポジトリは主に以下の機能群を提供します。

- J-Quants からの市場データ ETL（株価・財務・市場カレンダー）
- RSS ベースのニュース収集（前処理・SSRF 防御・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロレジーム判定
- ファクター計算・特徴量探索・統計ユーティリティ
- データ品質チェック
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- DuckDB を中心としたローカルデータ保存

以下はプロジェクトの概要、セットアップ、使用方法、ディレクトリ構成の説明です。

---

## 主な機能一覧

- data（ETL / カレンダー / ニュース収集 / J-Quants クライアント）
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分取得（prices / financials / calendar）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - JPX カレンダー管理（is_trading_day / next_trading_day / get_trading_days 等）
  - RSS ニュース収集（SSRF 対策、URL 正規化、記事ID生成）
  - J-Quants API クライアント（認証、ページネーション、レートリミット、保存関数）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）

- ai（ニュース NLP / 市場レジーム判定）
  - news_nlp.score_news: ニュース記事を銘柄別に集約して LLM に投げ、ai_scores を作成
  - regime_detector.score_regime: ETF(1321) の MA200 とマクロニュースセンチメントを合成して market_regime を判定

- research（ファクター計算・特徴量探索）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）

- config
  - .env（および .env.local）から環境変数を自動ロード（プロジェクトルートは .git または pyproject.toml で検出）
  - 必須環境変数チェック用ユーティリティ（Settings クラス）

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   - Python 3.10+ を推奨（コードは型アノテーションで | を使用）
   - 依存例: duckdb, openai, defusedxml など

   ```bash
   git clone <repo_url>
   cd <repo_dir>
   python -m pip install -e .
   ```

2. 必須環境変数を設定
   - 環境変数は OS 環境、またはプロジェクトルートの `.env` / `.env.local` から自動でロードされます。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な必須変数（Settings クラス参照）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード（本プロジェクト内の発注連携用）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - OPENAI_API_KEY        : OpenAI 呼び出し時に使用（関数引数で上書きも可）

   任意 / デフォルト:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / …（デフォルト: INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

3. ローカルデータディレクトリ作成
   - デフォルトで data/ 以下を使用する処理が多いため、必要に応じて作成してください。
   ```bash
   mkdir -p data
   ```

4. 必要パッケージ（例）
   - openai, duckdb, defusedxml など。setup.py / pyproject.toml に依存関係を記載してください。

---

## 使い方（簡易ガイド）

以下は代表的な操作のサンプルコードです。実運用ではログ設定・例外処理・API キー管理を適切に行ってください。

- DuckDB 接続を作成して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 25))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）の生成

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定している場合、api_key=None で可
n_written = score_news(conn, target_date=date(2026, 3, 25), api_key=None)
print("written:", n_written)
```

- 市場レジーム判定（market_regime への書込み）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 25), api_key=None)
```

- 監査ログ DB の初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続、テーブルとインデックスが作成されています
```

- ファクター計算 / 解析例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026, 3, 25))
normed = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注:
- OpenAI 呼び出しを含む関数（score_news, score_regime）は API エラーに対してフォールトトレラントな挙動（リトライ・失敗時は中立値）を持ちますが、API キーは必須です（引数で明示的に渡すか環境変数 OPENAI_API_KEY を設定）。

---

## 環境変数 / 設定（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY (必須 for LLM) — OpenAI API キー（score_news/score_regime 用）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（default: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG / INFO / ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 に設定すると .env 自動ロードを無効化

自動ロードはプロジェクトルート（.git または pyproject.toml を基準）で `.env` を読み込み、`.env.local` があればそれで上書きします。

---

## 推奨ワークフロー（例）

- データ取得（夜間バッチ）
  1. run_daily_etl をスケジューラ（cron / Airflow / GitHub Actions）で実行
  2. ETL 結果（ETLResult）をログ・Slack に送る
  3. ETL 後は data.quality.run_all_checks の結果を監視してアラート

- ニューススコア・レジーム判定
  - ETL 実行後に score_news → score_regime を順に実行（news window の時間整合性に注意）

- 発注・監査
  - 監査テーブルは init_audit_schema で作成。実際の注文フローでは order_requests を冪等キー（order_request_id）で挿入し、約定を executions に記録します。

---

## ディレクトリ構成

概略（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news）
    - regime_detector.py      — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS ニュース収集
    - calendar_management.py  — 市場カレンダー管理・判定
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - monitoring/                — （監視用ロジック / SQLite 対応など 想定）
  - execution/                 — （発注連携関連）
  - strategy/                  — （戦略定義 / シグナル生成）
  - otherモジュール...

（上記は主要ファイルの抜粋です。プロジェクト内にさらに補助モジュールが含まれます。）

---

## 開発 / テストについての注意

- DuckDB を多用するためテストでは in-memory DB（":memory:"）を使うと便利です。
- OpenAI / J-Quants API 呼び出しは外部依存のため、ユニットテストではモック（unittest.mock.patch）してください。コード内には _call_openai_api の差し替えを想定した設計や、J-Quants の HTTP 呼び出しのリトライ/キャッシュが組み込まれています。
- .env 自動ロードはプロジェクトルート検出に依存します。テスト実行時に意図しない .env を読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ライセンス / 貢献

- 本リポジトリのライセンス情報およびコントリビューション手順はプロジェクトルートの LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

---

README に書ききれない細かい設計意図や各関数の詳細仕様はソース内の docstring に豊富に記載されています。まずは ETL を動かしてデータが揃うことを確認し、score_news / score_regime を順に実行して結果の流れ（ai_scores → market_regime）を把握することを推奨します。必要であれば、README をベースに運用手順書やデプロイ手順書（systemd / k8s / Airflow など）を追加できます。