# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株のデータプラットフォーム・研究・シグナル生成・監査・ニュース/AI 統合を想定したライブラリ群です。  
DuckDB をデータレイヤに、J-Quants（株価 / 財務 / カレンダー）や RSS ニュース、OpenAI（LLM）を外部データソースとして組み合わせ、ETL / 品質チェック / ファクター計算 / ニュースセンチメント / 市場レジーム判定 / 監査ログを提供します。

バージョン: 0.1.0

---

## 主要機能

- ETL（デイリー）パイプライン
  - J-Quants から差分取得・冪等保存（prices / financials / market_calendar）
  - 市場カレンダーの自動先読み・バックフィル
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- データ基盤ユーティリティ
  - DuckDB への保存関数（冪等）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）

- ニュース収集 & NLP
  - RSS フィードの取得・前処理・raw_news 保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）計算

- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離 + マクロニュース LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を判定

- リサーチ機能
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - 将来リターン計算 / IC（Spearman） / 統計サマリー
  - Zスコア正規化ユーティリティ

- 設定管理
  - .env / 環境変数から設定を自動ロード（プロジェクトルート検出）
  - 必須設定は Settings 経由で取得（未設定時は例外）

---

## 必要な環境 / 依存パッケージ（例）

- Python 3.9+
- pip パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（プロジェクトではシンプルな標準ライブラリ実装を優先していますが、OpenAI SDK と DuckDB は必須です）

例: requirements.txt に以下を含めることを推奨
```
duckdb
openai
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または必要なパッケージを個別にインストール:
     - pip install duckdb openai defusedxml

4. 開発インストール（オプション）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須の環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN （J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD （kabu API 用パスワード）
     - SLACK_BOT_TOKEN （Slack 通知に使用する場合）
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（score_news / score_regime を使う場合）
   - 任意 / デフォルト値
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な API / サンプル）

以下は Python 内でライブラリを利用する簡単な例です。DuckDB の接続は `duckdb.connect()` を直接使います。

- ETL（1日分のデータ取得）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算（ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込み銘柄数:", written)
```

- 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログDB の初期化（監査専用 DB を作りたいとき）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# ここで signal_events / order_requests / executions テーブルが作成されます
```

- 研究用ファクター計算（例：モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- 設定参照（Settings）
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live)
```

---

## 注意点 / 設計上の方針（抜粋）

- Look-ahead バイアス防止のため、target_date を明示し、内部で `date.today()` を参照しない実装が多く採用されています。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われます。
- OpenAI 呼び出しは JSON mode（厳密な JSON 出力を想定）で行われ、失敗時はフォールバック/スキップする設計です。
- RSS 収集は SSRF 対策（スキーム検証・プライベートアドレス検査・リダイレクト検査）や最大受信バイト制限などセキュリティに配慮しています。
- 自動で .env をロードしますが、テスト時などに無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージのエントリ（__version__）
- config.py — 環境変数 / 設定管理（Settings）
- ai/
  - __init__.py — ai パブリック API
  - news_nlp.py — ニュースセンチメントのスコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - etl.py — ETL 結果再エクスポート
  - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — 品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログスキーマ定義 / 初期化
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - news_collector.py — RSS 取得・前処理
- research/
  - __init__.py
  - factor_research.py — ファクター計算 (Momentum/Value/Volatility)
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記は主要ファイルのみ。詳細はソースを参照してください）

---

## よくある質問 / トラブルシュート

- .env を読み込まない／別ファイルを使いたい
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。独自ロードしたい場合は os.environ に手動で設定してください。

- OpenAI のレスポンスが不正（JSON でない）
  - モデル応答が JSON でない場合、関数はログを出しフォールバック（スコア 0.0 やスキップ）します。必要に応じてリトライやプロンプトの改善を行ってください。

- DuckDB のパスを変更したい
  - 環境変数 `DUCKDB_PATH` を設定するか、直接 duckdb.connect("path") を渡して使用してください。

---

## 貢献 / 開発

- 既存の設計方針（Look-ahead 防止、冪等性、セキュリティ考慮）を尊重して機能拡張してください。
- テストは外部 API をモック化して実行することを推奨します（OpenAI 呼び出しやネットワークアクセスは差し替え可能な内部関数を用意しています）。

---

README は以上です。追加で含めたいサンプルや .env.example、CI / テスト手順などがあれば教えてください。