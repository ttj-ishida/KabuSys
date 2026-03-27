# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / DuckDB を使ったデータETL、ニュースのNLPスコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（オーディット）用テーブルなどを提供します。

主な対象
- 日本株（日足・財務・カレンダー）を用いた研究・バックテスト基盤
- ニュースを LLM（OpenAI）でセンチメント解析して銘柄スコアを生成
- 市場レジーム判定（ETF + マクロニュース）
- DuckDB を利用したローカルデータストアと冪等な ETL / 保存処理

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（OS 環境変数優先）
  - 必須設定は Settings クラス経由で取得（未設定時は例外）
- データ ETL（J-Quants API）
  - 株価日足（raw_prices）取得・保存（ページネーション・レート制御・リトライ）
  - 財務データ（raw_financials）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新 / バックフィル / 品質チェック機能（quality モジュール）
- ニュース収集
  - RSS フィード取得、前処理、SSRF 保護、raw_news への冪等登録
- ニュースNLP（LLM）
  - 銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores へ保存（score_news）
  - レート制限・リトライ・レスポンス検証を実装
- レジーム判定（regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM スコアを合成して market_regime に書き込み（score_regime）
- 研究用ユーティリティ（research）
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions など監査用テーブルの初期化ユーティリティ（冪等、UTC タイムスタンプ）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）

（プロジェクトの pyproject.toml / requirements.txt が存在する場合はそちらを参照してください）

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements がある場合はそれを使う）
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # 追加で必要なパッケージがあればここに追記
   ```

4. 開発版インストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数 / .env

自動読み込み順序（優先度高→低）:
1. OS 環境変数
2. .env.local
3. .env

自動ロードはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基準に行います。自動ロードを無効化したい場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（README の抜粋）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news/regime の呼び出しで使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 開発環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

基本的な .env の例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な呼び出し例）

以下は Python REPL / スクリプトからの利用例です。必要に応じて DuckDB 接続を作成して渡します。

- DuckDB 接続の作成例
```py
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（run_daily_etl）
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのスコアリング（score_news）
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written} ai_scores")
```

- 市場レジームのスコアリング（score_regime）
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化
```py
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn をアプリで使う
```

- ファクター計算（研究）
```py
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- LLM（OpenAI）を使う処理は OPENAI_API_KEY が必要です。未設定だと ValueError を投げます。
- ETL や保存処理は冪等性を考慮して実装されていますが、バックテスト用途では Look-ahead バイアスに注意して使用してください（各関数はその点を配慮して実装されています）。
- ネットワーク呼び出し部分はリトライやレート制御が組み込まれています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                    — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                 — ニュース NLP スコアリング（score_news）
  - regime_detector.py          — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py                 — ETL パイプライン (run_daily_etl 等)
  - etl.py                      — ETLResult 再エクスポート
  - jquants_client.py           — J-Quants API クライアント / 保存関数
  - news_collector.py           — RSS 収集と前処理
  - calendar_management.py      — 市場カレンダー管理・営業日ヘルパ
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore_normalize）
  - audit.py                    — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py          — Momentum / Volatility / Value 等
  - feature_exploration.py      — 将来リターン / IC / 統計サマリー
- research、ai、data 配下に多数の補助関数・ユーティリティが実装されています。

---

## 開発・テストに関するメモ

- 自動環境変数ロードは .env / .env.local をプロジェクトルートから読み込みます。テストで自動ロードをオフにする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ニュース収集では外部リソース（RSS）を扱うため、テスト時はネットワーク呼び出しをモックしてください（モジュール内で _urlopen 等を差し替え可能）。
- OpenAI 呼び出し部分（news_nlp、regime_detector）はテスト用に内部呼び出し関数を mock.patch で差し替えられるよう設計されています。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスや貢献方法などを追記してください）

---

質問や改善点があれば教えてください。コードベースに合わせて README をさらに詳細化したり、セットアップ用スクリプト例（systemd / cron / GitHub Actions ワークフロー）を追加できます。