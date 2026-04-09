# KabuSys

日本株向けのデータプラットフォームと自動売買・研究ユーティリティ群を提供するパッケージです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などの機能を含みます。

主な設計方針の特徴:
- ルックアヘッドバイアス対策（日時を安易に参照しない、ETLが取得日時を記録する等）
- DuckDB を中心にしたローカルデータ保存と idempotent（冪等）な保存処理
- 外部 API 呼び出しにはリトライ・レート制御を組み込み（J-Quants / OpenAI）
- テスト容易性を考慮した設計（API 呼び出しの差し替え箇所など）

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl の提供（市場カレンダー → 株価 → 財務 → 品質チェック）

- ニュース収集・NLP
  - RSS からニュースを安全に収集（SSRF対策、トラッキングパラメータ除去、正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄毎ニュースセンチメントのスコア化（ai_scores へ保存）
  - ニュースウィンドウは前日15:00 JST〜当日08:30 JST に対応

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成
  - market_regime テーブルへの冪等書き込み

- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ

- 監査（オーディット）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化（DuckDB）
  - order_request_id を冪等キーとしたトレーサビリティ設計

- その他
  - 環境変数管理（.env 自動ロード、オーバーライドルール）
  - LINE 通知や kabuステーション API 等の設定ポイント（トークンを環境変数で管理）

---

## 要件 / 推奨環境

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 主な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS ソース）

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。ここでは代表的なパッケージを挙げています。）

インストール例（仮）:
```bash
python -m pip install duckdb openai defusedxml
# パッケージを開発インストールする場合
pip install -e .
```

---

## 環境変数（重要）

.env または実行環境の環境変数から設定を読み込みます。読み込み順は OS 環境 > .env.local > .env です。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須 / 重要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（ETL の認証に使用）
- OPENAI_API_KEY (必須: news_nlp / regime_detector を使う場合)  
  OpenAI API キー
- KABU_API_PASSWORD (必須: kabu API を使用する実行環境で)  
  kabuステーション API のパスワード

その他の設定（任意・デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_FILL_MODE: paper トレードのフィルモード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視パラメータ

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境作成（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール:
   - pyproject.toml / requirements.txt がある場合はそれを使用
   例:
   ```bash
   pip install -r requirements.txt
   # または最低限
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定:
   - プロジェクトルートに `.env` または `.env.local` を作成し上記の必須変数を設定します。
   - 自動ロードは config モジュールがプロジェクトルート（.git または pyproject.toml を探す）を探索して行います。

5. データディレクトリ作成（必要に応じて）:
   ```bash
   mkdir -p data
   ```

---

## 使い方 — よく使う例

以下は Python から直接呼び出す基本的な例です。詳細は各モジュールの関数ドキュメント（コード内 docstring）を参照してください。

- DuckDB 接続を開く:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants からの差分取得・保存・品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコア（ai_scores に書き込む）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込み件数: {written}")
```

- 市場レジーム判定（market_regime テーブルへ書込）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算：
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- 監査テーブル初期化（監査用 DuckDB を別に作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は初期化済みの DuckDB 接続
```

- 市場カレンダー更新ジョブ（夜間バッチ）:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved: {saved}")
```

注意:
- OpenAI を呼ぶ関数は API キー（OPENAI_API_KEY）を環境変数または関数引数で渡す必要があります。
- J-Quants の ETL は JQUANTS_REFRESH_TOKEN を利用して id_token を取得します。
- run_daily_etl 等は内部で例外を捕捉して処理を継続する設計ですが、エラー詳細は戻り値 ETLResult.errors / quality_issues で確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数と .env 自動読み込みロジック / Settings
- ai/
  - __init__.py
  - news_nlp.py        — ニュースを銘柄別に集約して OpenAI でスコア（ai_scores への書込）
  - regime_detector.py — ETF 1321 MA とニュースセンチメントを合成して market_regime を生成
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETLResult の再エクスポート
  - stats.py              — zscore_normalize 等の統計ユーティリティ
  - quality.py            — データ品質チェック（欠損・スパイク・重複・日付）
  - calendar_management.py— 市場カレンダーの判定 / 更新ロジック
  - news_collector.py     — RSS 収集（SSRF 対策・正規化）
  - audit.py              — 監査ログテーブル初期化（signal/order/execution）
- research/
  - __init__.py
  - factor_research.py    — momentum/volatility/value の計算
  - feature_exploration.py— 将来リターン / IC / 統計サマリー 等
- research/*, ai/*, data/* 内には多数の補助関数と詳細実装があります。

（上記は抜粋です。実際のリポジトリの全ファイルを参照してください。）

---

## 実運用上の注意 / ベストプラクティス

- 機密情報（APIキー / トークン）は .env に平文で置くより、安全なシークレット管理（Vault 等）を推奨します。開発時のみ .env を使用してください。
- 本プロジェクトは実際の発注ロジックとは切り離して設計されていますが、実際に発注機能を組み合わせる場合は十分なリスク制御と二重チェック（order_request_id の冪等化、テスト環境での paper_trading 等）を行ってください。
- OpenAI 呼び出しにはコスト・レート制限が伴います。batch サイズ・リトライ設定を実運用に合わせて調整してください。
- DuckDB ファイルのバックアップ戦略やディスク容量監視を行ってください（設定で閾値チェックあり）。

---

README にまとめきれない細かい挙動（SQL スキーマ、各関数の引数仕様、ログの意味など）はソースの docstring に詳細に記載しています。開発や運用の際は各モジュールの docstring を参照してください。質問や補足があれば用途に合わせた具体例（例: 初回 ETL の実行手順、OpenAI 呼出しのモック方法 など）を追加で作成します。