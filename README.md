# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants からのデータ取得、DuckDB を使ったデータ永続化、ニュースの収集と LLM によるセンチメント評価、研究用ファクター計算、監査ログ（発注→約定トレース）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと自動売買基盤（研究〜運用）を支えるユーティリティ群です。主な機能は以下の通りです。

- J-Quants API 経由での株価・財務・マーケットカレンダー取得（ページネーション・リトライ・レート制御）
- DuckDB を使った ETL / 永続化（冪等保存、品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄別）およびマクロセンチメント合成による市場レジーム判定
- 研究向けファクター計算（モメンタム／バリュー／ボラティリティ等）、特徴量探索（将来リターン・IC 等）
- 監査ログ（signal → order_request → executions をトレース可能な監査スキーマ）初期化ユーティリティ
- 環境変数/.env ベースの設定管理（自動ロード機構、優先順位 .env.local > .env、OS環境変数優先）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証・リトライ・ページネーション・保存関数）
  - pipeline: 日次 ETL の実行（差分フェッチ、保存、品質チェック）
  - news_collector: RSS 取得・パース・前処理・raw_news への保存補助
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ作成 / 初期化（監査用 DuckDB DB 作成）
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.score_news: ニュース記事を銘柄別に集約し LLM でセンチメント評価、ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）の 200 日 MA 偏差とマクロニュースの LLM スコアを合成して market_regime テーブルへ保存
- research/
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ
- config.py: 環境変数 / .env 読み込み、settings オブジェクトで設定を参照可能

---

## セットアップ手順（開発環境向け）

※以下はリポジトリ側に requirements.txt 等が存在しない前提での推奨手順です。実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

1. Python 環境
   - Python 3.10+ を推奨（型注釈に Union | などを利用）
2. リポジトリをクローン
   - git clone <repo-url>
3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
4. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml
   - （プロジェクトに応じて追加の依存をインストール）
5. パッケージとしてインストール（開発用）
   - pip install -e .

### 環境変数 / .env

プロジェクトルートに `.env` と `.env.local` を置けます。自動読み込みの優先順位:
OS 環境変数 > .env.local > .env

自動ロードを無効化するには:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で使用）

主要な環境変数（必須となるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用。引数で注入可能）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（モニタリング用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...、デフォルト INFO)

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主な API と実行例）

以下はライブラリをプロジェクトに組み込んで使う基本例です。すべての操作は DuckDB 接続を受けます。

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコア合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマを初期化する（監査用 DB を作成）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別 DB パスを指定
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 注意点 / 設計上の考慮

- Look-ahead bias 対策
  - 多くのモジュールで内部的に date.today() 等を参照しない設計を採用。API 呼び出しや計算は明示的な target_date に依存します。
- 冪等性
  - ETL の保存関数は ON CONFLICT DO UPDATE を使い冪等に保存します。
- フェイルセーフ
  - LLM/API の失敗時に致命的な例外を上げず、適切にフォールバック（例: マクロセンチメント=0.0）する処理が組み込まれています。
- 自動 .env 読み込み
  - パッケージは import 時にプロジェクトルートの .env / .env.local を自動で読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能です。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要ファイル・モジュール構成はおおよそ以下の通りです（src/kabusys 以下）:

- kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py (公開インターフェース)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
  - ai/
  - monitoring/ (予備: README 要件に含まれていたが実装はモジュールに依存)
  - その他: strategy, execution（パッケージ公開名に含まれるが該当実装は別途）

上記はソース内の主要モジュールを抜粋しています。詳細は各モジュールの docstring を参照してください。

---

## 開発・デバッグのヒント

- ログレベルは環境変数 LOG_LEVEL で制御できます（例: LOG_LEVEL=DEBUG）。
- OpenAI 呼び出しなど外部 API はユニットテストでモック化する設計が想定されています（内部の _call_openai_api を patch するなど）。
- DuckDB によるクエリは SQL を多用しており、パフォーマンス最適化の余地がある部分はログとクエリを参照して調整してください。
- news_collector は SSRF 対策や受信サイズ制限を持っています。RSS ソースを追加する際は DEFAULT_RSS_SOURCES を編集してください。

---

## ライセンス / 貢献

（この README のテンプレートにはライセンスが含まれていません。実際のプロジェクトでは LICENSE ファイルを追加してください。）  

バグ報告や機能改善の提案は issue を立ててください。プルリクエストは歓迎します。

---

何か追加で README に含めたい実行手順や CI 設定、具体的な .env.example のテンプレート等があれば教えてください。必要に応じて README に追記します。