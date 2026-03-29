# KabuSys

日本株向けの自動売買・データプラットフォームライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレーサビリティ）、および市場レジーム判定までを含む一連の処理を提供します。

バージョン: 0.1.0

---

## 特長（概要）

- J-Quants API との連携による株価・財務・カレンダーの差分取得（レートリミット／リトライ処理、トークン自動リフレッシュ対応）
- DuckDB を用いたローカルデータベース保存（冪等保存、ON CONFLICT）
- 日次 ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS）と LLM による銘柄別ニュースセンチメント評価（gpt-4o-mini の JSON Mode を想定）
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ（Zスコア）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）のスキーマ初期化ユーティリティ

---

## 機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し、取得・保存
  - pipeline: ETL（run_daily_etl, run_prices_etl, ...）
  - quality: データ品質チェック（run_all_checks 等）
  - news_collector: RSS 収集・前処理
  - calendar_management: 市場カレンダー操作（is_trading_day 等）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize など
- ai/
  - news_nlp.score_news: ニュースを LLM に送って ai_scores を作成
  - regime_detector.score_regime: 市場レジーム判定（ma200 + マクロセンチメント）
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - 環境変数の自動読み込み (.env / .env.local)、Settings クラス

---

## 必要な依存パッケージ（例）

以下はソース内で明示的に利用されている主要パッケージです。実際のパッケージ名やバージョンはプロジェクトの配布物に合わせてください。

- Python 3.10+
- duckdb
- openai (OpenAI の公式 SDK)
- defusedxml
- （標準ライブラリで処理しているため requests 等は不要。ネットワークは urllib を使用）

インストール例:
```bash
python -m pip install duckdb openai defusedxml
```

プロジェクトのセットアップ方法は配布形式により変わります（パッケージ化されていれば `pip install .` 等）。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要な依存パッケージをインストール
   ```bash
   python -m pip install -U pip
   python -m pip install duckdb openai defusedxml
   ```
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（config モジュールが自動で読み込みます）。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 用）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注機能を実装する場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
     - DUCKDB_PATH — 保存先 DuckDB ファイル（既定: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（既定: data/monitoring.db）
     - KABUSYS_ENV — development | paper_trading | live
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要ユースケース）

以下は Python REPL / スクリプトからの呼び出し例です。`duckdb` を介して DB 接続を渡して操作します。

- DuckDB 接続を作成し ETL を実行する（1日分）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Settings で定義されたパス（.env により設定可能）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```
- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続
```

- 研究系ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

- 設定の読み取り（Settings）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

注意:
- AI 関連（score_news, score_regime）は OPENAI_API_KEY が必要です。引数に api_key を直接渡すこともできます。
- ETL / 保存関数は冪等に設計されています（ON CONFLICT 等）。

---

## 実行上の注意点と設計方針（要約）

- ルックアヘッドバイアス対策: 内部関数は date.today() を直接参照しない設計（関数に target_date を明示的に与える）。
- API 呼び出しはリトライ・バックオフ・レート制御を備える（J-Quants / OpenAI）。
- 失敗耐性: 外部 API の失敗はフェイルセーフ（影響を局所化し全体処理は継続）する設計のところが多い。
- DuckDB 保存は可能な限り冪等を担保（ON CONFLICT / DELETE→INSERT の構成）。
- NewsCollector は SSRF 対策、XML パースの安全化、受信サイズ制限などの防御策を実装。

---

## ディレクトリ構成（主要ファイル）

プロジェクトのルートに `src/kabusys` 配下に各モジュールがあります。主要ファイルを抜粋します:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - (その他: pipeline 用の ETLResult 再エクスポート etc.)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - (将来的に strategy/ execution/ monitoring などを拡張可能)

---

## 追加情報 / トラブルシュート

- .env の自動読み込みは project root（.git または pyproject.toml のある親ディレクトリ）を基準に行われます。CWD に依存しないため、パッケージ配布後でも安定して動作します。
- テストや CI で自動環境変数読み込みを無効にしたい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB の executemany に空リストが渡せないケース（古い DuckDB バージョン）をコード側で配慮していますが、環境の DuckDB バージョンが古い場合はアップデートを検討してください。
- OpenAI SDK の挙動やバージョンによって例外クラス名や status_code の取り扱いが変わる可能性があるため、SDK の互換性に注意してください。

---

## ライセンス / 貢献

（ここにはプロジェクトのライセンスやコントリビュート方法を記載してください。README のテンプレートとしては空欄ですが、実運用では必須です。）

---

必要であれば、README に含めるサンプル .env.example、より具体的なコマンドラインツール例（CLI スクリプト）や CI 用の設定例も作成できます。どの情報を追加しますか？