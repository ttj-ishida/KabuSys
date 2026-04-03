# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント算出）、リサーチ用ファクター計算、監査ログ・オーディット機能などを提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス防止」「DuckDB を中心としたローカル永続化」「外部 API の堅牢な呼び出し（リトライ・レート制御）」です。

---

## 主な機能

- データ取得 / ETL
  - J-Quants 経由での株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（ページネーション・リトライ・レート制限対応）
  - ETL 結果を表す ETLResult（品質チェック結果を含む）
- ニュース収集・前処理
  - RSS からのニュース収集（URL 正規化・SSRF 対策・XML 安全パーサ）
  - news_symbols テーブルとの紐付け等（raw_news 保存）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを ai_scores に書き込む（gpt-4o-mini / JSON Mode を利用）
  - 市場マクロセンチメント + ETF MA200乖離を合成して市場レジーム判定（bull / neutral / bear）
  - API 呼び出しのリトライ・フェイルセーフ（失敗時はスコア 0 にフォールバック）
- リサーチ用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB SQL を主体）
  - 将来リターン計算、IC（Information Coefficient）計算、Z-score 正規化など
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合（未来日付・非営業日データ）検出
  - QualityIssue オブジェクトで問題を集約
- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理
  - order_request_id を冪等キーとして二重発注防止

---

## 必要条件（推奨）

- Python 3.10+
- 必要なライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

（パッケージの細目はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（簡易）:
     - pip install duckdb openai defusedxml
   - またはプロジェクトルートに requirements.txt / pyproject.toml があれば:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env / .env.local を読み込みます。
   - 自動ロードを無効化する場合は環境変数を設定:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等で使用）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用。引数で注入することも可能）
   - 他（任意/デフォルトあり）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEM/DISK 閾値 等

   - .env.example を参考に .env を作成してください（リポジトリに同梱されているはずの例を参照）。

---

## 使い方（簡易サンプル）

以下は最小限の利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続準備と日次 ETL の実行

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照して Path を返します
conn = duckdb.connect(str(settings.duckdb_path))

# target_date を指定して ETL を実行（None = 今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OpenAI API キーを環境変数に入れていれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（マクロセンチメント + ETF 1321 MA200 乖離）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB 初期化

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

# 別ファイルで監査テーブルだけ管理したい場合
audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

- 研究用関数（例: モメンタム計算）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{date, code, mom_1m, mom_3m, mom_6m, ma200_dev}, ...]
```

---

## よく使うモジュール一覧

- kabusys.config
  - Settings: 環境変数のラッパー（自動 .env ロード、必須チェック）
- kabusys.data
  - jquants_client: J-Quants API の取得 / DuckDB 保存ロジック
  - pipeline: run_daily_etl / 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・保存
  - quality: データ品質チェック
  - calendar_management: 市場カレンダー関連ユーティリティ（is_trading_day 等）
  - audit: 監査テーブル作成 / 初期化
  - stats: zscore_normalize など
- kabusys.ai
  - news_nlp.score_news: ニュース NLP スコアリング（ai_scores へ書込）
  - regime_detector.score_regime: 市場レジーム判定（market_regime へ書込）
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（抜粋）

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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit の初期化ユーティリティなど
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring / strategy / execution / など（パッケージエクスポートに含まれる可能性）

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに補助モジュールが含まれます。）

---

## 注意事項 / 運用上のポイント

- OpenAI 呼び出しを行う機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しにはコストとレーテンシが発生するためバッチ化やリトライ挙動を理解した上で運用してください。
- J-Quants API の利用には有効なトークン（JQUANTS_REFRESH_TOKEN）が必須です。get_id_token は自動でリフレッシュを行いますが、設定ミスや権限切れに注意してください。
- DuckDB に対する大量の INSERT は executemany を使うように実装されています。DuckDB のバージョンに応じた挙動差に注意してください（コード内に互換性対応あり）。
- news_collector は外部 RSS の扱いに SSRF 対策・サイズ上限・XML 攻撃対策（defusedxml）などを実装していますが、デプロイ環境でのネットワーク設定・プロキシ等の挙動を確認してください。
- 自動で .env を読み込む機構があります（プロジェクトルート検出）。テストなどで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発 / 貢献

- コーディング規約・テスト・CI 等はリポジトリのルールに従ってください。各モジュールは単体でテスト可能なように依存注入（APIキー、DB 接続、sleep関数の差し替え等）を考慮して実装されています。
- 大きな変更を行う場合は ETL・品質チェック・監査（DDL）に影響がないかを確認してください。

---

この README はリポジトリにあるソースコードの機能と設計方針をまとめたものです。より詳細な実装・使用例は各モジュール（kabusys/data, kabusys/ai, kabusys/research）内のドキュメント文字列（docstring）を参照してください。