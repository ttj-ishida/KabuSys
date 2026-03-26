# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。J-Quants API や RSS ニュース、OpenAI（LLM）を活用してデータ収集（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注/約定トレース）などの機能を提供します。

---

## 主要な特徴（機能一覧）

- データ ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存
  - 差分取得 / バックフィル / ページネーション対応
  - DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集 & 前処理
  - RSS フィード取得（SSRF 対策、サイズ上限、トラッキングパラメータ除去）
  - 記事正規化・ID生成・raw_news への保存

- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini を想定）による銘柄別センチメント（ai_scores）生成（バッチ・リトライ処理）
  - マクロ記事からマーケットセンチメントを判定し、ETF（1321）200日移動平均乖離と合成して市場レジーム（bull/neutral/bear）を算出

- リサーチ（ファクター計算）
  - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20）、流動性、バリュー（PER, ROE）などの定量ファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ

- データ品質チェック
  - 欠損、スパイク、重複、将来日付／非営業日データ検出（QualityIssue を返却）

- カレンダー／営業日管理
  - market_calendar を用いた営業日判定・next/prev/trading days 算出
  - JPX カレンダーの夜間更新ジョブ

- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査テーブル定義、初期化ユーティリティ（DuckDB）
  - 発注フローのトレーサビリティ（UUID によるチェーン）

- 設定管理
  - .env / .env.local / 環境変数からの設定読み込み、Settings オブジェクト経由でアクセス

---

## 必要条件 / 事前準備

- Python 3.10+
  - （コードで | 型注釈などを使用しているため 3.10 以上が推奨）
- 主な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリを使用

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## 環境変数（主なもの）

KabuSys は .env（プロジェクトルート）と環境変数から設定を読み込みます（デフォルト: OS 環境変数 > .env.local > .env）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数例：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の呼び出し時に使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の例（プロジェクトルートに作成）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env をプロジェクトルートに作成し必須変数を設定

5. DuckDB データベースの準備（任意）
   - デフォルトでは settings.duckdb_path = data/kabusys.duckdb に保存されます
   - 監査用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb 接続
     ```

---

## 使い方（代表的な例）

以下は Python コードでのライブラリ利用例です。実行は仮想環境内で行ってください。

- DuckDB 接続を作って日次 ETL を実行する（例）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント）を実行:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```
- マーケットレジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）:
```python
import duckdb
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: モメンタム）:
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の mom_1m / mom_3m / mom_6m / ma200_dev を含む dict のリスト
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

- 監査スキーマ初期化（任意）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意:
- OpenAI 呼び出し（news_nlp / regime_detector）は OPENAI_API_KEY を参照します。引数で api_key を渡すこともできます。
- ETL / API 呼び出しはネットワークを使用します。適切な API キーとネットワーク設定を用意してください。

---

## 自動読み込みと無効化

kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local を自動読み込みします。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルと説明）

（src/kabusys 配下の主要モジュール）

- src/kabusys/__init__.py
  - パッケージのエントリ。バージョン情報等。

- src/kabusys/config.py
  - 環境変数・設定管理（Settings オブジェクト）

- src/kabusys/ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py: マクロセンチメントと ETF MA200 を合成して市場レジームを判定
  - __init__.py: score_news のエクスポート

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py: 日次 ETL パイプライン（run_daily_etl など）
  - etl.py: ETLResult の公開再エクスポート
  - news_collector.py: RSS 取得・記事前処理・raw_news 保存
  - calendar_management.py: market_calendar 管理、営業日ロジック、calendar_update_job
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログスキーマ作成 / 初期化ユーティリティ
  - __init__.py

- src/kabusys/research/
  - factor_research.py: Momentum / Volatility / Value 等の計算
  - feature_exploration.py: 将来リターン計算、IC 計算、統計サマリー、rank
  - __init__.py

- （その他）
  - strategy / execution / monitoring 等はパッケージ API の一部として想定（__all__ に含まれるが、実装が別にある場合があります）

---

## 設計上の留意点（運用時）

- Look-ahead bias 防止:
  - 各モジュールは target_date パラメータを受け取り、内部で date.today() を直に参照しない設計を心がけています。バックテスト用途では必ず過去データのみを参照できるようにしてください。

- フェイルセーフ設計:
  - LLM / API 呼び出しはリトライやフォールバック（例: macro_sentiment = 0.0）して処理を継続する実装が多くあります。

- 冪等性:
  - DuckDB への保存は可能な限り ON CONFLICT / DELETE → INSERT の形で冪等に行われます。ETL は部分失敗があっても既存データを不用意に消さないよう配慮しています。

- テスト容易性:
  - 内部の API 呼び出し（OpenAI / urllib 等）は関数をモックできるよう分離されています（単体テストで差し替え可能）。

---

## 貢献・ライセンス

- （この README では省略）プロジェクトに CONTRIBUTING.md や LICENSE があればそちらを参照してください。

---

この README はコードの一部（src/kabusys 以下）に基づいて作成しています。実際のリポジトリにはさらにドキュメントや設定ファイル（pyproject.toml / requirements.txt / .env.example など）が含まれている可能性があります。運用・デプロイ前にそれらを参照し、API キーやパスワードの管理に十分ご注意ください。