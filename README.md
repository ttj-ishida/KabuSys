# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー／約定トレーサビリティ）など、運用に必要なコンポーネントを揃えています。

---

## 主な機能

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄リスト、JPXマーケットカレンダーの取得／保存
  - レート制御・認証リフレッシュ・リトライを備えたクライアント（jquants_client）
- ETL パイプライン
  - run_daily_etl を中心とした差分取得・保存・品質チェック（data.pipeline）
- ニュース収集
  - RSS から記事を収集し raw_news / news_symbols に保存（news_collector）
  - SSRF 対策、受信サイズ制限、URL 正規化等の安全対策を実装
- ニュースNLP / LLM スコアリング
  - 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価して ai_scores テーブルへ保存（ai.news_nlp）
  - マクロニュースを用いた市場レジーム判定（ai.regime_detector）
  - API 呼び出しはリトライ・フォールバック（失敗時は中立スコア）実装
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility 等）、将来リターン、IC（Spearman）、Zスコア正規化（research.*, data.stats）
- データ品質チェック
  - 欠損、スパイク、重複、日付整合性チェック（data.quality）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等、発注〜約定のトレーサビリティ用スキーマ定義・初期化（data.audit）
- 環境設定管理
  - .env / .env.local の自動ロード（config）と Settings ラッパー

---

## 前提・依存

- Python 3.10+
  - 型注釈（X | None）などを使用しているため 3.10 以上を想定しています
- DuckDB
  - 内部データベースとして duckdb を想定（pip install duckdb）
- OpenAI SDK
  - OpenAI API を呼び出すためのパッケージ（openai）
- defusedxml
  - RSS パース時の安全対策（defusedxml）
- ネットワークアクセス
  - J-Quants API、OpenAI API、各種 RSS ソースへのアクセス

推奨インストールパッケージ（例）
- duckdb
- openai
- defusedxml

（requirements.txt がある場合はそちらを利用してください）

---

## 環境変数

config.Settings クラスから各種設定を取得します。主な環境変数:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション（証券会社 API）のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境 (development | paper_trading | live), デフォルト development
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY — OpenAI API キー（AI 関連処理で利用）

.env 自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）から .env と .env.local を自動的に読み込みます
  - 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低限）pip install duckdb openai defusedxml

4. .env の作成
   - プロジェクトルートに .env（および .env.local）を作成し、必要な環境変数を設定
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb

5. ディレクトリ作成（必要に応じて）
   - mkdir -p data

6. 初期 DB 構築（監査 DB の初期化例）
   - Python REPL またはスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()

---

## 使い方（代表的な API）

以下は簡単なサンプルコードです。実運用ではログ設定や例外処理を追加してください。

- 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニューススコアを生成する（OpenAI API キー必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
conn.close()
```

- 市場レジーム判定（ETF 1321 を基準）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

- ファクター計算（研究用）
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
znorm = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
conn.close()
```

- 監査スキーマの初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されます
conn.close()
```

- データ品質チェックを実行
```python
import duckdb
from kabusys.data.quality import run_all_checks
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
conn.close()
```

注意:
- AI 関連 API は外部サービス（OpenAI）に依存します。テスト時は各モジュールの内部呼び出しをモックする設計（例: _call_openai_api のパッチ）になっています。
- J-Quants API 呼び出しは jquants_client の get_id_token / fetch_* を使用します。API キーやレート制御に注意してください。

---

## 自動読み込みされる .env の動作

- パッケージ import 時（kabusys.config モジュール）にプロジェクトルートを探索し、.env を自動ロードします。
  - 探索条件: このファイルの親ディレクトリから上方に .git または pyproject.toml が見つかる場所をプロジェクトルートと見なします。
- 読み込み順（優先度低 → 高）
  - .env（override=False）：既に OS 環境にあるキーは上書きしない
  - .env.local（override=True）：上書き許可（ただし OS 環境で既に設定されたキーは保護）
- 自動ロードを無効にするには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

（この README を配置するリポジトリの src/kabusys 配下を要約）

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
    - etl.py (ETL 用の公開型再エクスポート)
    - jquants_client.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (パッケージ公開候補 — 実装は repository を参照) 
  - strategy/   (戦略関連モジュール用ディレクトリ)
  - execution/  (発注実行関連モジュール)

（上のリストは実装済みモジュールの抜粋です。詳細はソースツリーを参照してください）

---

## 開発・運用上の注意

- Look-ahead bias の防止
  - 多くの関数は date.today() を直接参照せず、明示的に target_date を受け取る設計になっています。バックテスト・運用時は target_date を明示してください。
- フェイルセーフ設計
  - LLM API の失敗は中立スコア（0.0）などでフォールバックし、パイプライン全体の停止を避けます。ただしログを必ず確認してください。
- テスト容易性
  - 外部 API 呼び出し部分は差し替え（モック）しやすい実装になっています（例: _call_openai_api, _urlopen）。
- DB 操作は可能な限り冪等（ON CONFLICT / INSERT … DO UPDATE）にしています。

---

## 参考 / 次のステップ

- 実運用に移す前に、ローカルで DuckDB に対するスキーマ初期化・ETL のリハーサルを行ってください。
- OpenAI や J-Quants のクォータ／課金・レート制限については事前に確認してください。
- 発注（kabu API）を有効にする場合は sandbox（paper_trading）環境で十分に検証してください（KABUSYS_ENV を paper_trading に設定）。

---

必要であれば README に含めるコマンド例や .env.example のテンプレート、CI／デプロイ手順も作成できます。どの部分を追加しますか？