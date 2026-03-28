# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群で構成されています。

- J-Quants API を使った株価・財務・カレンダー等の差分 ETL
- RSS ニュース収集と前処理（SSRF 対策等を実装）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- ETF の移動平均等を用いた市場レジーム判定（bull / neutral / bear）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）用スキーマ初期化ユーティリティ

設計上の主要な方針は「ルックアヘッドバイアス回避」「ETL の冪等性」「API 再試行・レート制御」「DuckDB を中心としたオンディスク DB 管理」です。

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークンリフレッシュ対応）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存処理（SSRF 対策、トラッキングパラメータ除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ用スキーマの初期化（init_audit_schema / init_audit_db）
  - stats: Zスコア正規化など共通統計ユーティリティ
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメント取得 → ai_scores へ書込
  - regime_detector.score_regime: ETF の MA200 とマクロニュースの LLM スコアを合成して market_regime に書込
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数読み込み（.env/.env.local の自動ロード）, settings オブジェクト

---

## 要件（推奨）

- Python 3.10+
- 主な外部ライブラリ:
  - duckdb
  - openai
  - defusedxml
- （ネットワーク接続が必要）J-Quants API、OpenAI API アクセス権

依存パッケージはプロジェクト側で requirements.txt を用意してください。最低限のインストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを開発モードでインストール
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン（プロジェクトルートに .git または pyproject.toml があることを利用して .env 自動検出を行います）:
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # または上の個別インストール例
   pip install -e .
   ```

3. 環境変数を設定（.env をプロジェクトルートに配置するのが簡単です）。主要な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: モニタリング通知用
   - DUCKDB_PATH: (例) data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト時に便利）

   .env の例（プロジェクトルート/.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

注意: config モジュールはプロジェクトルートを .git または pyproject.toml から探索し、その配下の .env / .env.local を自動読込します。自動読込を無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（クイックスタート）

以下は主要なユーティリティ関数の簡単な使用例です。各例は Python スクリプトや REPL で実行できます。

- DuckDB 接続の作成（settings 参照）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に書き込む:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None → 環境変数 OPENAI_API_KEY を利用
print("scored:", n_written)
```

- 市場レジーム（ETF 1321）スコアリング:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は初期化済みの DuckDB 接続
```

- 研究用ファクター計算:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- OpenAI 呼び出しを伴う関数（score_news, score_regime）は API キーが必要です。api_key 引数で直接渡すか、環境変数 OPENAI_API_KEY を設定してください。
- すべての関数は「ルックアヘッドバイアス防止」のために内部で date / target_date を明示的に扱う設計です。date.today() を無条件に参照するような使い方は避けてください（テスト/バックテストの再現性確保）。

---

## ディレクトリ構成

主要なファイル/モジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 & settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save系）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査スキーマ初期化（init_audit_schema / init_audit_db）
    - etl.py                        — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/ (プレースホルダ: モニタリング関連モジュール想定)
  - strategy/  (プレースホルダ: 戦略実装用モジュール想定)
  - execution/ (プレースホルダ: 発注連携モジュール想定)

（実際のファイル全体は src/kabusys 以下にあります。上記は主要なモジュールの抜粋です）

---

## 開発・テストに関する補足

- config の自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml で検出して行います。CI や単体テストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して下さい。
- OpenAI 呼び出し部分は個別の内部 _call_openai_api を定義しており、テスト時は unittest.mock.patch で差し替えてモック化できます。
- DuckDB はローカルファイル（例 data/kabusys.duckdb）を想定しています。初回はスキーマ定義（別途 schema initializers）が必要になります（本 README のスコープ外）。監査ログ用のスキーマ初期化は data.audit.init_audit_db / init_audit_schema を参照してください。
- ETL 実行結果は ETLResult オブジェクトとして返され、to_dict() でシンプルにシリアライズできます。

---

## 最後に

この README はコードベースに含まれる主な機能と利用イメージをまとめたものです。各モジュールの詳細な API ドキュメント（関数ごとの引数・戻り値・例外）や初期スキーマ定義、運用手順（ジョブスケジューラ設定・監視）については別途ドキュメントを用意してください。必要であれば README を拡張して運用手順やよくあるトラブルシュートも追加します。