# KabuSys

日本株向け自動売買・データプラットフォームのコアライブラリ（README）。  
このリポジトリはデータ収集（ETL）、ニュースNLP、ファクター計算、監査ログ、J-Quants / kabu API クライアント等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの基盤ライブラリです。  
主な目的は以下です。

- J-Quants API を用いた市場データ（株価・財務・カレンダー等）の差分 ETL
- RSS ニュース収集と OpenAI を用いたニュースセンチメント評価（ai_scores）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル → 発注 → 約定）を保存する監査スキーマと初期化ユーティリティ
- 各種データ品質チェック、マーケットカレンダー管理、news_collector（RSS）等

設計方針として「ルックアヘッドバイアス回避」「冪等性（idempotency）」「フェイルセーフ」「APIレート管理」を重視しています。

---

## 主な機能一覧

- ETL（data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - quality チェック（欠損・スパイク・重複・日付不整合）
- J-Quants クライアント（data.jquants_client）
  - fetch / save（daily quotes, financials, market calendar, listed info）
  - レート制御・リトライ・トークン自動リフレッシュ
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、SSRF 対策、トラッキング除去、raw_news への保存を想定
- ニュース NLP（ai.news_nlp）
  - raw_news / news_symbols を集約 → OpenAI（gpt-4o-mini）でセンチメント取得 → ai_scores へ保存
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime を更新
- 研究用ユーティリティ（research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 統計ユーティリティ（data.stats）
  - zscore_normalize など
- 監査ログ（data.audit）
  - 監査スキーマの初期化（init_audit_schema / init_audit_db）、テーブル定義（signal_events / order_requests / executions）
- 設定管理（config）
  - .env 自動ロード（プロジェクトルート検出）と Settings オブジェクト（環境変数アクセス）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（PEP 604 の union 型 `X | Y` を使用）
- 主要依存（プロジェクトに requirements.txt がない場合は下記をインストールしてください）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, datetime, json, logging, pathlib など

例（pip）:
```
pip install duckdb openai defusedxml
```

プロジェクトを editable インストールする場合（セットアップが揃っていれば）:
```
pip install -e .
```

---

## 環境変数 / .env

自動で .env（プロジェクトルート）および .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主に使用する環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ('development','paper_trading','live')（デフォルト development）
- LOG_LEVEL: ログレベル ('DEBUG','INFO','WARNING','ERROR','CRITICAL')（デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必要）

.env 例（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルで動かす場合）

1. Python をインストール（推奨 3.10+）。
2. 仮想環境を作成・有効化（任意）。
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール:
   - pip install duckdb openai defusedxml
4. プロジェクトルートに `.env` を作成（.env.example を参考に必要な値を設定）。
5. DuckDB 用ディレクトリを準備（`data/` 等）:
   - mkdir -p data
6. （任意）監査用 DB 初期化:
   - see 使い方の例

---

## 使い方（主要な例）

以下は Python REPL やスクリプトから呼び出す例です。事前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続の確立:
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュース NLP スコア（ai_scores へ書き込む）:
```
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY の環境変数を使う
print(f"scored {count} codes")
```

- 市場レジーム判定:
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を初期化（監査専用 DB を作る）:
```
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# テーブルが初期化され、UTC タイムゾーンが設定されます
```

- 研究用関数の利用例:
```
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026,3,20))
# mom は各銘柄の辞書リストを返す
```

注意点:
- ai モジュールは OpenAI を呼び出します。API コストやレート制限に注意してください。
- 各関数はルックアヘッドバイアス回避のため、内部で datetime.today() を直接参照しない設計です（target_date を明示してください）。
- テスト時はモジュール内の HTTP / OpenAI 呼び出し関数をモック可能です（docstring に記載）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py (パッケージ定義、__version__)
- config.py (環境変数・設定管理: Settings)
- ai/
  - __init__.py
  - news_nlp.py (ニュース NLP スコアリング、OpenAI 連携)
  - regime_detector.py (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント、保存ロジック)
  - pipeline.py (ETL パイプライン、run_daily_etl 等)
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py (RSS 収集・前処理)
  - calendar_management.py (市場カレンダー管理 / 営業日判定)
  - quality.py (データ品質チェック)
  - stats.py (zscore_normalize 等)
  - audit.py (監査ログスキーマ初期化)
- research/
  - __init__.py
  - factor_research.py (calc_momentum, calc_value, calc_volatility)
  - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)

各モジュールには docstring に処理フロー・設計方針・フェイルセーフの説明が記載されています。

---

## 開発・テストに関する補足

- 環境設定:
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）の検出に依存します。テストで自動ロードを避けたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- モック性:
  - OpenAI 呼び出しや HTTP オープン関数はモック可能なレイヤを持つため、ユニットテストで外部依存を差し替えられます（docstring に置換方法の記載あり）。
- ログ:
  - Settings.log_level でログレベルを制御できます。

---

## 注意事項 / セキュリティ

- RSS 取得では SSRF 対策・コンテンツ長制限・defusedxml を用いた XML パース等の安全対策を組み込んでいますが、運用時はランタイム環境のネットワークポリシーも考慮してください。
- API キーやシークレットは `.env` に保存する場合でも適切に管理（アクセス制御・CI/CD の secret 管理）してください。
- 実取引（kabu ステーション接続 / ライブ設定）時は十分な検証とリスク管理を行ってください（KABUSYS_ENV を `live` にセットすると実行環境が本番挙動を想定するフラグが有効になります）。

---

もし README に追加したい具体的な手順（例えば Docker 化、CI 設定、requirements.txt の雛形、より詳細な使用例や SQL スキーマ定義）などがあれば教えてください。README をそれに合わせて拡張します。