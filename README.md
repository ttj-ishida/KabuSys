# KabuSys

KabuSys は日本株のデータ収集・品質管理・ファクター研究・ニュースNLP・市場レジーム判定・監査ログ管理を含む自動売買／リサーチ基盤ライブラリです。本リポジトリは ETL（J-Quants 経由）、DuckDB を用いた時系列データ管理、OpenAI を利用したニュースセンチメント解析、ファクター計算や市場レジーム判定などの主要処理を提供します。

主な設計方針
- ルックアヘッドバイアスを防止する設計（内部で date.today()/datetime.today() を無暗に参照しない）
- DuckDB をデータベースとして利用し、ETL は冪等性を保つ
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- テスト容易性を考慮した分離設計（API クライアントや内部呼び出しの差し替えが可能）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（無効化可能）
  - settings オブジェクトから必要な設定値を提供
- データ取得 / ETL（J-Quants 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの差分取得
  - 差分・バックフィル・ページネーション対応、ID トークン自動リフレッシュ、レート制御、リトライ
  - DuckDB への冪等保存（ON CONFLICT）
- データ品質チェック
  - 欠損、スパイク、主キー重複、日付不整合などのチェックと QualityIssue レポート
- ニュース収集
  - RSS フィード収集、前処理、SSRF 対策、トラッキングパラメータ除去、raw_news への冪等保存（設計に基づく）
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースをまとめて LLM に投げ、ai_scores を書き込む（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - OpenAI レート制御／リトライ、JSON mode のバリデーション
- 研究（Research）ユーティリティ
  - モメンタム / バリュー / ボラティリティ系ファクター計算
  - 将来リターン計算、IC（情報係数）計算、ランク化・Zスコア正規化
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定のトレーサビリティを保つ監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- カレンダー管理
  - 営業日判定、next/prev_trading_day、カレンダー更新バッチ（calendar_update_job）
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize）など

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の型注釈（X | Y）を使用）
- 主な依存ライブラリ（実行時に必要なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース など）

依存は pyproject.toml / requirements.txt がある想定です。ローカルで動かす場合は仮想環境を推奨します。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. インストール
   - pip install -e .  （パッケージとしてインストールできる場合）
   - または必要パッケージをインストール:
     - pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるパス）の .env / .env.local を自動読み込みします（既定）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用、関数引数でも渡せます）
- KABU_API_PASSWORD : kabuステーション API を使う場合のパスワード
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知を使う場合
- DUCKDB_PATH (任意) : デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意) : デフォルト data/monitoring.db

簡単な .env.example（README 用の例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## 使い方（主要なユースケース）

以下は最小限の利用例です。DuckDB 接続に conn（duckdb.connect(...)） を渡して各関数を使います。

1) settings を読む（環境変数から）
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

2) DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

3) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニュースセンチメントスコア生成（OpenAI API キーは env または引数で渡す）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示することも可能
count = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("scored:", count)
```

5) 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

6) 監査DB 初期化（監査専用 DB ファイル生成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

7) カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

8) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

注意点
- OpenAI を利用する処理は API キー（OPENAI_API_KEY）を環境変数か関数引数で与える必要があります。関数はフェイルセーフ設計で、API 失敗時にはゼロスコアやスキップで継続する場合がありますが、ログで確認してください。
- J-Quants 呼び出しは get_id_token を用いトークン自動リフレッシュ、レート制御、リトライを行います。JQUANTS_REFRESH_TOKEN を .env に設定してください。

---

## よくある操作コマンド（例）

- パッケージを編集インストール:
  - pip install -e .

- DuckDB を起動して SQL を確認:
  - python -c "import duckdb; conn=duckdb.connect('data/kabusys.duckdb'); print(conn.execute('SELECT 1').fetchall())"

- ログレベルを変更:
  - export LOG_LEVEL=DEBUG

- 自動 .env 読み込みをオフ:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイル群（抜粋）です。各モジュールは用途別に整理されています。

- src/kabusys/
  - __init__.py  （パッケージ初期化、version）
  - config.py    （環境設定 / .env ロード / Settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py         （ニュース NLP / score_news）
    - regime_detector.py  （市場レジーム判定 / score_regime）
  - data/
    - __init__.py
    - calendar_management.py  （マーケットカレンダー管理）
    - etl.py                  （ETL インターフェース）
    - pipeline.py             （日次 ETL パイプライン）
    - stats.py                （統計ユーティリティ）
    - quality.py              （データ品質チェック）
    - audit.py                （監査ログ定義・初期化）
    - jquants_client.py       （J-Quants API クライアント + 保存関数）
    - news_collector.py       （RSS ニュース収集）
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py       （Momentum/Value/Volatility 等）
    - feature_exploration.py   （将来リターン、IC、rank、factor_summary）
  - ai (既述)
  - research (既述)
  - その他（strategy / execution / monitoring 等のモジュールが想定される）

---

## ロギング・監視

- ログレベルは環境変数 LOG_LEVEL（DEBUG/INFO/...）で制御。
- 監視や実行プロセスの PID 管理などの設定は settings（pid_file_path, cpu_threshold_pct 等）から参照できます。

---

## 開発・テストに関するヒント

- OpenAI / J-Quants 呼び出し部分は差し替え／モックしやすい設計になっています（内部の _call_openai_api などを unittest.mock.patch で差し替え可能）。
- DuckDB をインメモリ（":memory:"）で使えばテストが容易です。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（ユニットテスト時に有用）。

---

## サポート / 貢献

バグ報告やプルリクエストは issue/PR を通じてお願いします。設計方針（ルックアヘッドバイアス防止、冪等性、フェイルセーフ）を尊重するようにしてください。

---

README はここまでです。必要であれば以下の情報を追加できます:
- pyproject.toml / requirements.txt の具体的な内容
- .env.example の完全版
- より詳細な API リファレンス（各関数の引数／返り値のサンプル）
- CI / テストの実行方法

どれを追加しますか？