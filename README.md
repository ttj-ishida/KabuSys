# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
データ収集（J-Quants）、ETL、データ品質チェック、特徴量・ファクター計算、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（発注・約定トレース）などを含むモジュール群を提供します。

---

## 概要

KabuSys は日本株の定量投資／自動売買システムのための基盤ライブラリです。  
主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への冪等保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメント評価（ai_scores）
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログスキーマ（signal / order_request / execution）と初期化ユーティリティ

設計上、バックテスト時のルックアヘッドバイアス回避や、APIリトライ/フェイルセーフを重視しています。

---

## 機能一覧

- データ取得・保存
  - J-Quants からの daily quotes / financial statements / market calendar 取得（ページネーション対応、レート制御）
  - DuckDB へ ON CONFLICT DO UPDATE 方式で冪等的に保存
- ETL
  - 差分取得、自動バックフィル、品質チェック（run_daily_etl）
  - ETL 結果を表す ETLResult 型
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合を検出（QualityIssue）
- ニュース処理 / NLP
  - RSS 取得と前処理（SSRF 対策、サイズ上限、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア生成（score_news）
  - マクロニュース + ETF 200日MA を用いた市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライやフェイルセーフを備える
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー ファクター計算（prices_daily / raw_financials から）
  - 将来リターン計算、IC 計算、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の DDL とインデックス作成
  - 監査DB初期化ユーティリティ（init_audit_db）

---

## セットアップ手順

1. Python（推奨 3.10+）をインストールします。

2. リポジトリをクローンし、開発環境を作成します。

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストールします（例）。プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください。

   ```
   pip install duckdb openai defusedxml
   # 開発インストール（パッケージを editable にする）
   pip install -e .
   ```

   ※実際のプロジェクトで使用している依存パッケージが別にあれば適宜追加してください。

4. 環境変数の設定

   - 必須（実行する機能に依存）
     - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（ETL 時に使用）
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp / regime_detector 使用時）
   - kabu API 等（発注連携を行う場合）
     - KABU_API_PASSWORD, KABU_API_BASE_URL
   - 任意（通知等）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - データベースパス
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）

   自動読み込み:
   - パッケージはプロジェクトルートにある `.env` / `.env.local` を自動読み込みします（OS 環境変数より下位、`.env.local` は `.env` を上書き）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は主要機能の簡単な利用例です。実行前に必要な環境変数を設定してください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジームを判定して market_regime に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクターを計算する（例：モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "銘柄のモメンタムを計算しました")
```

- 監査DB（監査ログ）を初期化する

```python
from kabusys.data.audit import init_audit_db
db_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

注意点:
- OpenAI を使う関数はデフォルトで環境変数 `OPENAI_API_KEY` を参照します。テスト時は api_key を引数で注入できます。
- OpenAI 呼び出しはリトライ・フェイルセーフを備えていますが、APIキーやネットワークに依存します。
- ETL / 保存処理は DuckDB スキーマ（raw_prices, raw_financials, market_calendar, ai_scores, prices_daily など）が前提です。スキーマ初期化はプロジェクトの別モジュールで行っている想定です。

---

## 主要モジュール & ディレクトリ構成

リポジトリ内の主なモジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（自動 .env ロード、Settings）
  - ai/
    - __init__.py               — news_nlp.score_news の再エクスポート
    - news_nlp.py               — ニュースセンチメント（銘柄別）と OpenAI 呼び出し
    - regime_detector.py        — ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - pipeline.py               — ETL パイプライン & run_daily_etl / ETLResult
    - etl.py                    — ETLResult の再エクスポート
    - news_collector.py         — RSS 取得と raw_news 保存ユーティリティ
    - calendar_management.py    — 市場カレンダー管理（is_trading_day 等）
    - quality.py                — データ品質チェック（QualityIssue）
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - audit.py                  — 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py    — calc_forward_returns / calc_ic / factor_summary / rank

（上記はこの README 作成時点での主要ファイル一覧です）

---

## 実装上の注意・設計メモ

- ルックアヘッドバイアス防止: 多くの関数は `date` / `target_date` を引数に取り、内部で `datetime.today()` を参照しないよう実装されています。バックテストでの利用に適しています。
- 冪等性: DuckDB への保存は基本的に ON CONFLICT DO UPDATE（あるいは INSERT … DO NOTHING）で実装し、再実行に耐えます。
- フェイルセーフ: OpenAI / 外部 API 呼び出しは再試行やフォールバック（スコア 0.0 など）を行い、例外を投げない挙動を基本としています（ただし認証が無い場合は ValueError を出す）。
- セキュリティ: news_collector は SSRF 対策（ホストのプライベート判定、リダイレクト検査）や XML 解釈安全ライブラリ（defusedxml）を使用しています。

---

## よくある質問（FAQ）

Q: OpenAI API キーが無いとどうなる？  
A: news_nlp.score_news / regime_detector.score_regime は API キーを必要とします。引数 `api_key` にキーを渡すか、環境変数 `OPENAI_API_KEY` を設定してください。未設定の場合は ValueError が発生します（設計として明示的に失敗させるため）。

Q: .env はどの順序で読まれる？  
A: OS 環境変数 > .env.local > .env の順で読み込まれます。パッケージは自動的にプロジェクトルート（.git または pyproject.toml を探索）から読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

Q: DuckDB のデフォルトパスは？  
A: Settings.duckdb_path のデフォルトは `data/kabusys.duckdb` です。環境変数 `DUCKDB_PATH` で変更できます。

---

ご要望があれば、README に具体的なセットアップスクリプト（requirements.txt、DB スキーマ初期化手順）、またはデモ用の Jupyter ノートブック用サンプルを追加します。必要な箇所を指定してください。