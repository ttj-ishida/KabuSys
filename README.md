# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
市場データの ETL、ニュースの収集・NLP スコアリング、ファクター計算、監査ログ（オーダー／約定トレース）、市場カレンダー管理、J-Quants / kabuステーション など外部 API との連携機能を含みます。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件（依存）
- セットアップ手順
- 環境変数（主な設定）
- 使い方（簡単な例）
- データベース初期化（監査ログ）
- 開発時のヒント
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株のデータ収集・品質チェック・ファクタ調査・AI によるニュースセンチメント評価・市場レジーム判定・監査ログ（シグナル→発注→約定のトレース）など、投資戦略開発と運用を支える基盤的モジュール群を提供します。  
設計上、以下を重視しています：
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）
- DuckDB を用いたローカルデータ管理
- 外部 API 呼び出しに対する堅牢なリトライ / レート制御
- 冪等性（ETL 保存は ON CONFLICT / DO UPDATE 等で上書き）

---

## 機能一覧
主な機能（モジュール）：
- kabusys.config: 環境変数 / .env ファイルの自動読み込み・設定管理
- kabusys.data:
  - ETL パイプライン（J-Quants からの株価・財務・カレンダー取得）
  - カレンダー管理（営業日判定 / next/prev_trading_day 等）
  - ニュース収集（RSS）と前処理
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - J-Quants クライアント（認証・ページネーション・保存）
  - 監査ログ（signal_events / order_requests / executions テーブル）と初期化ユーティリティ
  - 統計ユーティリティ（Zスコア正規化 等）
- kabusys.ai:
  - news_nlp.score_news: ニュースを LLM で銘柄ごとにセンチメント評価して ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定
- kabusys.research:
  - ファクター算出（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

---

## 必要条件（依存）
最低限の主要依存ライブラリ（バージョン固定はリポジトリの管理に依存）：
- Python 3.10+
- duckdb
- openai (新しい SDK を想定: OpenAI クラスを利用)
- defusedxml
- その他標準ライブラリ（urllib 等）

インストール例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発用に setuptools 等が必要なら適宜追加
```

（注）この README はパッケージ配布形式に依存せず手早く動かすためのガイドです。プロジェクトに requirements.txt / pyproject.toml があればそちらを優先してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # 必要ならその他の依存を追加
   ```

3. 環境変数を設定（.env をプロジェクトルートに置く）
   - 自動ロード: kabusys.config はプロジェクトルートに .env / .env.local を探して自動で読み込みます（無効化可：KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 例として必要なキーは下記「環境変数」セクション参照。

4. DuckDB ファイル等のデータディレクトリを準備
   - デフォルトでは `data/kabusys.duckdb`（settings.duckdb_path）などが使われます。必要に応じてディレクトリを作成してください。

---

## 環境変数（主な設定）
以下はコード内で参照される主要な環境変数です。README 用の例:

必須（実運用で必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI（LLM）用 API キー（score_news / score_regime で未指定時に参照）

任意（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env の例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

- DuckDB 接続を作って ETL を実行する（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path と合わせる
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースをスコアリング（OpenAI API キーが環境変数に設定されている場合 api_key 引数は不要）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 を基準）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ専用の DB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続オブジェクト
```

- ファクター計算 / 研究:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## データベース初期化（監査ログ）
監査ログ（signal_events / order_requests / executions）テーブルを作成するユーティリティが用意されています。

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

init_audit_db は必要なディレクトリを作成し、UTC タイムゾーンを設定した上でテーブルとインデックスを冪等的に作成します。

---

## 開発・テスト時のヒント
- 自動で .env を読み込む処理はデフォルトで有効です。テストで明示的に環境を制御したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 API はテスト時にモック化（unittest.mock.patch）することが想定されています。コード中でも `_call_openai_api` などをモックする設計をしています。
- DuckDB への executemany に空リストを渡すと問題が出るバージョン（0.10 系）を考慮した実装になっています。空リストチェックを行ってください。

---

## ディレクトリ構成（主なファイル）
以下は src/kabusys 配下の主要構成を抜粋したものです。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py  (ETLResult 再エクスポート)
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...（ファクター/解析ユーティリティ）
  - ai/...（LLM 関連）
  - data/...（ETL / DB / API クライアント）

---

必要に応じて README に追加したい項目（例えば CLI の使い方、CI / テスト手順、詳細な設定例、.env.example のテンプレートなど）があれば教えてください。README の内容をプロジェクトの配布形式（pip 配布・コンテナ化など）に合わせて調整できます。