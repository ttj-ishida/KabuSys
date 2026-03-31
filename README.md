# KabuSys

日本株向けのデータパイプライン・リサーチ・自動売買基盤コンポーネント群です。J-Quants / kabuステーション / OpenAI 等と連携し、日次ETL、ニュースセンチメント解析、マーケットレジーム判定、ファクター計算、監査ログ等を提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「DuckDB を中心としたローカルデータプラットフォーム」「API 呼び出しは堅牢なリトライ・レート制御」「冪等性（idempotency）の重視」です。

---

## 機能一覧

- 環境変数／.env 読み込みと集中設定管理（kabusys.config）
  - 自動 .env ロード（.env → .env.local）を行い、テスト時は無効化可能
- データETL（kabusys.data.pipeline, jquants_client）
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・raw_news への冪等保存（SSRF／XML攻撃対策あり）
- ニュースNLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント算出 → ai_scores へ保存
  - バッチ／リトライ・JSON バリデーション等の実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して 'bull' / 'neutral' / 'bear' を算出 → market_regime に保存
- リサーチ用ファクター計算（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）、統計サマリ等
- 監査ログ（kabusys.data.audit）
  - signal → order_request → executions のトレーサビリティを保持する監査スキーマ初期化ユーティリティ
- ユーティリティ（kabusys.data.stats など）
  - Zスコア正規化などの共通統計処理

---

## 前提条件

- Python 3.9+（型ヒントで Union | を使っているため 3.10 推奨）
- ネットワーク接続（J-Quants / OpenAI）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他依存は pyproject.toml を参照）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストールします（プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）。

   例（pip）:

   ```bash
   pip install duckdb openai defusedxml
   pip install -e .
   ```

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードは .git または pyproject.toml を基準にルートを検出します）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 必須環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（執行系）
- SLACK_BOT_TOKEN — Slack 通知トークン（監視/通知用）
- SLACK_CHANNEL_ID — Slack チャンネルID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の自動ロード順序は OS 環境 > .env.local > .env（.env.local が上書き）です。プロジェクトルートが見つからない場合は自動ロードをスキップします。

---

## 使い方（よく使う API 例）

基本的に DuckDB 接続を作り、各モジュールの関数を呼び出します。

- DuckDB 接続例

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

### 日次 ETL を実行する

```python
from kabusys.data.pipeline import run_daily_etl

# conn は上で作成した DuckDB 接続
result = run_daily_etl(conn, target_date=None)  # target_date=None は今日
print(result.to_dict())
```

run_daily_etl は市場カレンダー取得 → 株価ETL → 財務ETL → 品質チェック の順で実行し、ETLResult を返します。

### ニュースセンチメント（銘柄ごとの ai_score）を計算する

OpenAI API キーを環境変数に設定しておくか、api_key 引数で渡します。

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
print(f"written: {n}")
```

- 注意:
  - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）
  - OpenAI 呼び出しはバッチ・リトライ実装あり
  - テスト時は kabusys.ai.news_nlp._call_openai_api を patch してモック可能

### 市場レジーム（market_regime）をスコアリングする

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # 1 を返す（成功）
```

- 内部処理:
  - ETF 1321 の 200 日 MA 乖離を計算
  - マクロキーワードでニュースを抽出し LLM に評価させる（gpt-4o-mini）
  - 乖離とマクロセンチメントを重み付けして合成、market_regime テーブルへ冪等書き込み

### 監査DBスキーマ初期化（注文監査用）

監査ログ専用 DB を初期化してスキーマを作成します。

```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
```

init_audit_db は transactional=True 相当でテーブルとインデックスを作成します（タイムゾーンは UTC に設定）。

### リサーチ API（ファクター計算例）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとのファクター辞書のリスト
```

他に calc_volatility, calc_value、research.feature_exploration の calc_forward_returns / calc_ic などが利用可能です。

---

## 開発・テストのヒント

- 環境変数自動ロードを無効化:
  - テストで .env を読み込みたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出しは各モジュールごとに private wrapper を提供しており、ユニットテスト時は該当関数を patch して差し替えられるようになっています（例: kabusys.ai.news_nlp._call_openai_api）。
- DuckDB を用いたテスト:
  - インメモリ DB を使うには `duckdb.connect(":memory:")` を利用できます。
- ロギング:
  - settings.log_level でログレベルを制御可能です（環境変数 LOG_LEVEL）。

---

## 主要なディレクトリ構成

（ファイルは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数管理・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（OpenAI）
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理（営業日判定、更新ジョブ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py — J-Quants API クライアント & DuckDB 保存関数
    - news_collector.py — RSS 収集・前処理・保存
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ等

---

## 例: .env.example

プロジェクトルートに .env.example を置き、コピーして必要な値を設定してください。

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## その他

- 本プロジェクトは Look-ahead バイアスを避ける設計を強く意識しています。各種関数は内部で date.today() や datetime.now() を不用意に参照しないように実装されています（明示的に target_date を渡すことが推奨されます）。
- 外部 API 呼び出しにはリトライ・レート制御・フェイルセーフが組み込まれています。API キー未設定時は明示的なエラーを出すため、運用前に必ず環境変数を確認してください。

---

必要があれば、README に実行コマンド例（systemd / cron / Airflow 用のスニペット）、pyproject.toml によるインストール手順、CI 用のテスト手順などを追加します。どの類の追加情報が必要か教えてください。