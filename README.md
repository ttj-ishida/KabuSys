# KabuSys

日本株向けのデータプラットフォーム & 自動売買（リサーチ・ETL・監査・AI分析）ライブラリです。  
本リポジトリは以下の機能群を提供します：データ取得（J-Quants）、ETL、データ品質チェック、ニュースの収集とLLMによるセンチメント評価、市場レジーム判定、ファクター計算、監査ログ（発注 → 約定のトレース）など。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）・財務情報・JPXカレンダーを差分取得し DuckDB に冪等保存
  - 日次パイプライン（run_daily_etl）でカレンダー→価格→財務→品質チェックを実行
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集・NLP（OpenAI）
  - RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - ニュースを銘柄別にまとめて LLM へ送り、ai_scores テーブルに書き込み（score_news）
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - 監査DBの初期化関数（init_audit_db / init_audit_schema）

---

## 前提（動作環境）

- Python 3.10+
- 必須ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- その他（利用機能に応じて）
  - ネットワークアクセス（J-Quants / RSS / OpenAI）
  - ローカルに DuckDB ファイルを格納できる環境

（プロジェクトに requirements.txt がある場合はそれを利用してください。なければ上記を pip でインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （追加でテストやその他ツールがあれば適宜インストール）
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的にロードされます（load順は OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注周り）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector に使用）

設定例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

settings は `kabusys.config.settings` 経由で参照できます（プロパティで path 型や bool 判定などを提供）。

---

## 使い方（主要な例）

以下はライブラリを直接インポートして使う例です。実行前に環境変数（OPENAI_API_KEY など）を用意してください。

- DuckDB 接続例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（LLM を使って ai_scores に書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されている前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（MA200 とマクロニュースの LLM 結合）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime result:", res)
```

- 監査DBの初期化（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブルとインデックスを作成します
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注記：
- score_news / score_regime は OpenAI API を呼び出します。API キーが必須です。
- ETL は J-Quants API を利用します。JQUANTS_REFRESH_TOKEN が必須です。
- 多くの関数は DuckDB 接続を直接受け取り、内部で SQL を実行します。バックテストやユニットテストではモックやインメモリ DuckDB(":memory:") を利用してください。

---

## config（.env）の自動読み込みについて

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、そのルートにある `.env` および `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - `.env.local` は .env を上書きします（override=True）。
- 自動読み込みを無効にしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

settings（kabusys.config.Settings）からは便利なプロパティが参照できます（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など）。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（version など）
  - config.py — 環境変数 / .env 管理、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄別にまとめ、OpenAI でスコア化して ai_scores に保存するロジック
    - regime_detector.py — ETF(1321) MA200 乖離とマクロニュース LLM を合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック含む）
    - pipeline.py — ETL のメインロジック（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得と raw_news への保存ロジック（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理、営業日判定ユーティリティ
    - quality.py — 品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize など）
    - audit.py — 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/regime_detector.py, ai/news_nlp.py — OpenAI 呼び出しのリトライ・フォールバック実装あり

各モジュールは設計方針として「ルックアヘッドバイアスを避ける（date.today() を直接参照しない）」「DuckDB のトランザクションや実行環境の互換性を意識する」などの配慮がされています。

---

## 運用上の注意点

- OpenAI や J-Quants へのリクエストにはレート制限や課金が関わるため、使用時はそれらを考慮してください。
- ETL 実行や LLM 呼び出しは再現性のためログを残すことを推奨します（settings.log_level で調整）。
- DuckDB のバージョンや SQL の互換性により executemany の振る舞いが異なる場合があるため、空パラメータの扱いに注意（コード内に互換性対策あり）。
- ニュース収集モジュールには SSRF 対策とレスポンスサイズチェックが組み込まれていますが、RSS ソースの信頼性には注意してください。

---

もし README に追加したい内容（例: CI 設定、開発ルール、より詳細な API リファレンス、サンプル .env.example）や、特定の機能の使用例（発注フロー、Slack 通知統合など）があれば教えてください。必要に応じて追記します。