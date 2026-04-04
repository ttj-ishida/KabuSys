# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI を利用した銘柄センチメント）、リサーチ用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを内包します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション・レートリミット対応・自動トークンリフレッシュ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検出（QualityIssue）
- ニュース収集
  - RSS からのニュース収集、前処理、raw_news への冪等保存、銘柄紐付け（SSRF対策・トラッキングパラメータ除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（ai_scores テーブルへ保存）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA 乖離 + LLM センチメントの合成）
  - 再試行・JSON バリデーション・バッチ処理対応
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等の因子計算（duckdb SQL ベース）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- 監査ログ（tracing）
  - signal_events / order_requests / executions といった監査テーブル定義と初期化機能
  - 監査用の専用 DuckDB 初期化 helper（UTC タイムゾーン固定、DDL の冪等性確保）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   ※ requirements ファイルはリポジトリに含まれていない想定です。最低限必要な主要依存は以下です:
   - duckdb
   - openai
   - defusedxml
   - typing-extensions (Python バージョンによる)
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   開発運用で必要な追加パッケージがあれば適宜インストールしてください。

4. パッケージを編集可能モードでインストール（ローカル開発用）
   ```
   pip install -e src
   ```

5. 環境変数設定  
   ルートに `.env` / `.env.local` を置くことで自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必要な主要環境変数は下記参照。

---

## 環境変数（例）

config モジュールで参照する主な環境変数:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, 監視用): data/monitoring.db
- OpenAI / NLP
  - OPENAI_API_KEY — OpenAI API キー（各 NLP 関数で未指定時に参照）
- kabu（発注）関連
  - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
  - KABU_API_BASE_URL (任意)
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- 実行環境 / ログ
  - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- その他監視ファイルパス等
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

簡単な `.env.example`（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API と例）

以下は Python スクリプト / REPL から呼ぶ想定の例です。DuckDB 接続は duckdb.connect(...) を使います。

- ETL（日次一括）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 個別 ETL（株価のみ）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
print(f"fetched={fetched}, saved={saved}")
```

- ニュース NLP（銘柄センチメントを ai_scores に保存）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scores written:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（監査用 DuckDB を生成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- リサーチ用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

注意点:
- 各関数は「ルックアヘッドバイアス」を避けるため内部で date.today() を使わない設計です。必ず target_date を明示的に渡してください（省略しているAPIもあるためドキュメント参照）。
- OpenAI 呼び出しは API キーが必要です。api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 呼び出しには JQUANTS_REFRESH_TOKEN が必要です。

---

## 監査 / データベースについて

- デフォルトの DuckDB ファイルパスは config.Settings.duckdb_path により "data/kabusys.duckdb"（相対）となります。必要に応じて環境変数 DUCKDB_PATH を設定してください。
- 監査テーブル初期化は data.audit.init_audit_db または data.audit.init_audit_schema を利用します。init_audit_db は parent ディレクトリの自動作成も行います。

---

## 注意事項 / 運用メモ

- 自動で .env をロードする機能があり、プロジェクトルート（.git または pyproject.toml の存在で判定）から `.env` と `.env.local` を順に読み込みます。テスト等で自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し周りは再試行・バックオフを実装しているものの、API レート・課金に注意してください。
- news_collector は RSS の SSRF 対策（ホスト検査、リダイレクト検査、レスポンスサイズチェック）を組み込んでいますが、運用上追加の制限が必要な場合は監査ログ等を確認してください。
- DuckDB の executemany に空リストを渡せないバージョンがある点（コード内に対処あり）や、SQL の互換性に注意して運用してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - etl.py (再エクスポート)
  - news_collector.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - (その他 jquants_client 内ユーティリティ等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/（その他モジュール群）
- (strategy / execution / monitoring) などのエクスポート予定箇所が __all__ に記載

（上記は主要ファイルのみ抜粋しています。詳細はソースツリーを参照してください）

---

## 開発 / テスト

- 各 API 呼び出し関数（特に OpenAI / HTTP 関連）はモック化を想定して設計されています（例: news_nlp._call_openai_api / regime_detector._call_openai_api を unittest.mock.patch により差し替え可能）。
- 自動環境変数ロードはテストで干渉する場合があるため、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## ライセンス / 貢献

（リポジトリに記載されている LICENSE を参照してください）

---

以上。README に記載が欲しい追加の項目（例: 具体的な SQL スキーマ、API レートプラン、CI 設定、サンプルワークフロー）などがあれば教えてください。必要に応じて追記します。