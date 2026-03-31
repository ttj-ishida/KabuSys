# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants からのデータ取得・ETL、ニュース収集・LLM によるニュースセンチメント評価、研究用ファクター計算、監査ログ（オーダー/約定トレース）などを提供します。

主な設計方針
- ルックアヘッドバイアス回避（内部で date.today() 等を不用意に参照しない）
- DuckDB を主なストレージとして使用（ETL は冪等に保存）
- OpenAI（gpt-4o-mini）を利用したニュース NLP、LLM 呼び出しはリトライやフォールバック実装あり
- API レート制御・SSRF 対策・入力バリデーション等の堅牢化

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイル自動読み込み（プロジェクトルート検出）と環境変数経由設定 (`kabusys.config.settings`)
- データ ETL / Data Platform
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - ETL パイプライン（差分取得、保存、品質チェック）
  - 市場カレンダー管理（営業日判定 / next/prev / SQ判定）
  - ニュース収集（RSS -> raw_news、SSRF・圧縮対策・前処理）
  - データ品質チェック（欠損値、重複、スパイク、日付整合性）
  - 汎用統計ユーティリティ（Zスコア正規化）
- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（ニュースNLP / レジーム判定）
  - news_nlp.score_news: 銘柄別ニュースを LLM に投げて ai_scores を生成
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースを合成して市場レジーム判定
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DuckDB DB 初期化 helper

---

## 前提・必須ソフトウェア

- Python 3.10+
- DuckDB（Python パッケージとして `duckdb`）
- OpenAI Python SDK（`openai`、ここでは OpenAI クライアントの使用を前提）
- defusedxml（RSS パースの安全化）
- その他標準ライブラリ（urllib 等）を使用

必要な Python パッケージの例（requirements.txt を作る場合）:
- duckdb
- openai
- defusedxml

インストール例:
```bash
python -m pip install duckdb openai defusedxml
```

（実際のプロジェクトでは setup.py / pyproject.toml に依存関係を明記してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをチェックアウト
2. Python 3.10 以上の仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. 環境変数設定
   - プロジェクトルートに `.env` を作成（リポジトリに .env.example があればそれを参照）
   - 必須キー（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使う）
     - KABU_API_PASSWORD: kabuステーション等のパスワード（必要に応じて）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知に使用する場合
   - データベースパス（任意、デフォルトあり）
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (モニタリング用)
   - 実行環境フラグ:
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
   - 自動 .env ロードを無効化する:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト時等）

5. DuckDB 用ディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な呼び出し例）

以下はライブラリをインポートして単発処理を行う例です。実行は Python スクリプトまたは REPL から可能です。

- ETL（日次パイプライン）を実行する例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（LLM）で銘柄別スコアを生成:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は監査テーブルが作成された DuckDB 接続
```

- 市場カレンダー操作例:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出しは API キー（環境変数 OPENAI_API_KEY）を必要とします。関数の api_key 引数で明示的に渡すことも可能です。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN を利用して id_token を取得します。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP): OpenAI API キー（score_news / score_regime 実行時）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB（デフォルト data/monitoring.db）
- KABUSYS_ENV: development|paper_trading|live（環境に応じた制御）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" をセットすると .env 自動ロードを無効化

settings のプロパティは `from kabusys.config import settings` で参照できます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                  -- ニュースセンチメント（LLM）
  - regime_detector.py           -- 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py       -- 市場カレンダー管理（営業日判定 etc.）
  - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
  - jquants_client.py            -- J-Quants API クライアント + 保存ロジック
  - news_collector.py            -- RSS ニュース収集・保存
  - quality.py                   -- データ品質チェック
  - stats.py                     -- 統計ユーティリティ（zscore_normalize）
  - audit.py                     -- 監査ログ (signal/order/execution) 初期化
  - etl.py                       -- ETL 公開インターフェース（ETLResult re-export）
- research/
  - __init__.py
  - factor_research.py           -- モメンタム・バリュー・ボラティリティ等
  - feature_exploration.py       -- 将来リターン / IC / 統計サマリー

---

## 開発・運用上の注意

- ルックアヘッドバイアスを避けるため、各関数は与えられた target_date を基準に前日のデータを参照するよう設計されています。バックテストで使用する場合は ETL により過去時点までのデータをあらかじめロードしてから使用してください。
- OpenAI 呼び出しや J-Quants 呼び出しはネットワークエラーやレート制限に対応したリトライロジックがありますが、運用時は API コストや制限に注意してください。
- news_collector は RSS の外部 URL を取得します。SSRF 対策 / レスポンスサイズ制限 / gzip 解凍上限等の安全対策が組み込まれています。
- DuckDB の executemany は空リストを受け付けないバージョン（例: 0.10）を想定したガードがあります。実運用では DuckDB のバージョンに注意してください。
- テスト時は環境変数自動読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）するとテストの独立性が高まります。

---

## 貢献

バグレポート、機能提案、Pull Request は歓迎します。README の不足や API の使いにくさに気づいたら Issue を作成してください。

---

以上。README の補足や特定機能の詳しいサンプル（例: ETL ジョブのスケジューリング、Slack 通知の実装例、DuckDB スキーマ定義の確認方法等）が必要でしたら教えてください。