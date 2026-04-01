# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼リサーチ / 自動売買補助ライブラリです。J-Quants からのデータ取得（ETL）、ニュースの収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクタ計算、監査ログ（約定追跡）などを一通りカバーするモジュール群を提供します。

主な想定用途:
- データパイプライン（日次 ETL）での株価 / 財務 / カレンダー取得
- ニュースを用いた銘柄ごとの AI センチメントスコア算出
- ETF とマクロセンチメントを用いた市場レジーム判定
- 研究用ファクター計算・統計解析
- 発注・約定までの監査ログ（DuckDB）初期化・管理

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境変数 / .env 自動読み込み（設定管理）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応、レート制限・リトライ実装）
  - 財務データ取得
  - JPX カレンダー取得
  - DuckDB へ冪等保存（ON CONFLICT）
- ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）による銘柄別センチメントスコア（score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成、score_regime）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量解析（IC、forward returns）
- 統計ユーティリティ（Zスコア正規化など）
- 監査ログ（signal_events, order_requests, executions）DDL と初期化ユーティリティ（init_audit_db）

設計上のポイント:
- Look-ahead バイアス対策（target_date を明示、内部で date.today() を不用意に参照しない）
- フェイルセーフ: API 失敗時は局所的にフォールバック（例: LLM 失敗時 macro_sentiment = 0）
- DuckDB ベースでローカルに素早く永続化・検査

---

## 前提条件

- Python 3.10 以上（PEP 604 の型記法 (A | B) を利用）
- 必須ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトにより追加パッケージが必要になる場合があります。必要に応じて追記してください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （開発時は editable install が便利）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートの .env または .env.local に環境変数を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD      — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（監視等で使用）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
   - 任意/既定値あり:
     - KABU_API_BASE_URL      — kabu API のベース URL（既定: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime で使用）
     - DUCKDB_PATH            — DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite（既定: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な例）

以下はライブラリを直接 Python から使う最小例です。target_date は明示的に渡すことを推奨します（Look-ahead バイアス回避）。

- DuckDB 接続を開く（既定のパスを使う場合）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュース NLP スコアを生成する（OpenAI API キーは env か引数で）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- ファクター計算 / 研究ユーティリティ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

- 監査ログ DB を初期化する（専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db

aud_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが初期化されます
```

注意点:
- OpenAI 呼び出しをテスト時に差し替える際は、モジュール内の _call_openai_api をモックすることが想定されています（news_nlp._call_openai_api, regime_detector._call_openai_api）。
- ETL / データ保存は DuckDB のテーブルスキーマが前提です。テーブル作成スクリプトや初期化処理が必要な場合はプロジェクト内のスキーマ初期化ユーティリティを実装してください。

---

## 自動読み込みと無効化

- config モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、.env と .env.local を自動で読み込みます。
- 自動読み込みを無効化するには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

主要ファイル / モジュールの概観:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメントスコア（score_news）
    - regime_detector.py    — ETF MA + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + 保存関数
    - pipeline.py           — ETL パイプライン（run_daily_etl 他）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS ニュース収集・前処理
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - audit.py              — 監査ログ DDL と初期化（init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    — momentum / value / volatility 計算
    - feature_exploration.py— forward returns / IC / factor_summary / rank
  - ai package, research package など必要なサブパッケージが含まれます

---

## 開発・テストのヒント

- LLM 呼び出しは外部 API を叩くため、単体テストでは _call_openai_api をモックしてください。
- news_collector では外部 HTTP を行うため、fetch_rss / _urlopen をモックしてネットワーク依存を排除できます。
- DuckDB はインメモリ ":memory:" 接続をサポートしており、テストで使いやすいです（例: duckdb.connect(":memory:")）。
- ETL のリトライ / ログはログレベルを DEBUG にすると挙動観察がしやすいです（LOG_LEVEL 環境変数）。

---

## ライセンス・貢献

（この README にはライセンスの記載がありません。実プロジェクトでは LICENSE ファイルを追加してください。）

貢献（Issue / PR）は歓迎します。大きな変更は設計方針（Look-ahead バイアス防止等）に留意して行ってください。

---

README の改善や追加してほしいサンプル（たとえば DB スキーマ定義、.env.example、CI 設定、実行スクリプト例 など）があれば教えてください。必要に応じて追記します。