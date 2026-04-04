# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → AI ニュースセンチメント → 戦略評価 → 監査ログ までの一連処理をサポートするモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアスの回避」「DuckDB を用いたローカル永続化」「API 呼び出しの堅牢なリトライとレート制御」「冪等性（idempotency）」です。

---

## 特徴（機能一覧）

- 環境変数 / .env の自動読み込みと型安全な設定取得（kabusys.config）
  - .env/.env.local をプロジェクトルートから自動ロード（無効化可）
- J-Quants API クライアント（jquants_client）
  - 株価日足、財務データ、上場銘柄情報、JPX カレンダー取得
  - レートリミット管理・トークン自動リフレッシュ・リトライ実装
  - DuckDB への冪等保存ユーティリティ
- ETL パイプライン（data.pipeline）
  - 日次 ETL（run_daily_etl）・個別ジョブ（prices/financials/calendar）
  - 品質チェックとの統合（data.quality）
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す
- ニュース収集（data.news_collector）
  - RSS フィード収集・SSRF 対策・トラッキングパラメータ除去・前処理
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査トレーサビリティを保証するスキーマ初期化（init_audit_db / init_audit_schema）
- 研究用モジュール（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - zscore 正規化ユーティリティ（data.stats）
- AI モジュール（ai）
  - ニュースのセンチメント取得（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を用いた JSON Mode 呼び出し、堅牢なリトライ処理

---

## 必要条件（依存関係）

主な Python ライブラリ（代表）:

- Python 3.9+（型アノテーションと一部構文を利用）
- duckdb
- openai (OpenAI の v1 SDK 想定)
- defusedxml

プロジェクトの実際の依存は pyproject.toml / requirements.txt を参照してください（本 README はコードベースからの概要説明です）。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用）
   ```bash
   pip install -r requirements.txt
   # または
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（デフォルト）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - .env のパースは shell 風のキー=値、`export KEY=val`、クォートやコメントにも対応します。

   最低限必要な環境変数（代表）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）

   任意・デフォルト値を持つ設定（例）:
   - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: デフォルト "data/monitoring.db"
   - KABUSYS_ENV: one of "development", "paper_trading", "live"（デフォルト "development"）
   - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）

   サンプル .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_pass
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要ユースケース・コード例）

以下は簡単な Python 例です。DuckDB 接続を作って ETL を回し、ニューススコアやレジーム判定を行う流れを示します。

- 基本インポートと設定参照
```python
import duckdb
from kabusys.config import settings

print("duckdb path:", settings.duckdb_path)
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# score_news は内部で OPENAI_API_KEY を参照するか、api_key を渡す
conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", written)
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブル・インデックスを作成します
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- AI 関連（news_nlp / regime_detector）は OpenAI の API キーを必要とします。API 呼び出しは堅牢にリトライ/フェイルセーフが組まれていますが、API コストとレート制限に注意してください。
- ETL / データ取得は J-Quants の利用規約に従ってください。J-Quants の API トークンは JQUANTS_REFRESH_TOKEN に設定します。

---

## .env の自動読み込みについて

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を検出すると、自動的に `.env`（既存環境変数は上書きしない）と `.env.local`（上書き可能）を読み込みます。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env のパースはシェル互換（export 形式・クォート・コメント）をサポートします。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下の主なファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings オブジェクト（settings）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント解析（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント、保存ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 収集、前処理（SSRF 対策あり）
    - calendar_management.py— JPX カレンダー取得・営業日判定ロジック
    - quality.py            — データ品質チェック
    - stats.py              — z-score 正規化など統計ユーティリティ
    - audit.py              — 監査ログスキーマ定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py— 将来リターン、IC、統計サマリー等
  - research/*、ai/*：研究用・AI 用のユーティリティ群

---

## 運用上の注意点

- データベース（DuckDB）ファイルや PID / フラグファイルのパスは Settings で指定可能（環境変数経由）。
- ETL は「部分失敗でも可能な限り続行し、結果を報告する」設計です。critical な問題は ETLResult や QualityIssue を通して上位に伝えられます。
- OpenAI / J-Quants の呼び出しはコスト・レート制限に注意して下さい。OpenAI 呼び出しは gpt-4o-mini の JSON Mode を利用する想定です。
- DuckDB の executemany に関する互換性注意（空リスト渡しを避ける処理が含まれています）。

---

## 参考: よくある操作例

- ETL を cron / サービスに組み込む場合、daily のジョブで run_daily_etl を呼び出して結果（ETLResult）を監視し、QualityIssue の severity が "error" の場合アラートを上げる等の運用が想定されます。
- 発注周り（監査ログ）の初期化は init_audit_db で行い、実運用では audit DB とデータ DB を分離して運用することを推奨します。

---

以上がこのコードベースの概要・セットアップ・使い方です。README に追加したい具体的なコマンド、サンプル .env.example、CI/デプロイ手順やユニットテストの記述を希望される場合は、用途（ローカル実行 / クラウド運用 / バックテスト用など）を教えてください。それに合わせて README を拡張します。