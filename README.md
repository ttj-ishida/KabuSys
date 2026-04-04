# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、研究（ファクター計算・特徴量解析）、AI ベースのニュース分析、監査ログ（発注〜約定のトレーサビリティ）などを含む設計になっています。

---

## 主要機能（概要）

- データ収集 / ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 差分 / バックフィルロジック、ページネーション、トークン自動リフレッシュ、レートリミット制御を実装
- ニュース収集・NLP
  - RSS 取得（SSRF 対策・トラッキング除去）→ raw_news に保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）と、マクロニュースによる市場レジーム判定
- 研究用モジュール
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue により詳細を収集（エラー / 警告判定）
- 監査（Audit）
  - signal_events / order_requests / executions テーブル等を通した発注〜約定のトレーサビリティ
  - 初期化ユーティリティ（DuckDB）を提供
- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルート検出）
  - 必須値検査・環境ごとのフラグ（development/paper_trading/live）

---

## 必要条件

- Python >= 3.10（型注釈で `X | None` を使用しているため）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# パッケージを editable install する場合（プロジェクトルートで）
pip install -e .
```

（プロジェクトに requirements.txt があればそちらを使ってください）

---

## 環境変数 / .env

KabuSys は自動でプロジェクトルート（.git または pyproject.toml を持つディレクトリ）を探索し、`.env` と `.env.local` を読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（README 用抜粋）:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等用 デフォルト: data/monitoring.db）
- KABUSYS_ENV: one of {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL: one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視関連

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定値はコード内で `from kabusys.config import settings` を介して参照できます（例: `settings.jquants_refresh_token`）。

---

## セットアップ手順（例）

1. リポジトリをクローンする
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   pip install -e .
   ```

3. .env を作成（上の例参照）
   - プロジェクトルートに `.env` を置くと自動で読み込まれます。
   - テスト時に自動ロードを無効にする場合: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

4. DuckDB を用意（デフォルトは data/kabusys.duckdb）
   - ディレクトリを作成:
     ```bash
     mkdir -p data
     ```
   - （オプション）監査用 DB 初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡単な例）

以下は主要なユースケースのサンプルコードです。Python スクリプトまたは REPL で実行できます。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを生成（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示するか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 19), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースのセンチメントを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
date0 = date(2026, 3, 19)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

- 監査テーブル初期化（既に別 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 実装上の注意（運用時のポイント）

- 自動読み込み: config モジュールはプロジェクトルートを探索して `.env` / `.env.local` を読み込みます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- OpenAI 使用時: API 呼び出しでは JSON mode を使い（厳密な JSON 出力を期待）、エラーやパース不良時にはフェイルセーフで 0.0 を返す実装です（スコアリング処理は部分失敗しても他を壊さない設計）。
- Look-ahead Bias 対策: 多くの関数は内部で datetime.today() を直接参照せず、target_date を明示的に渡すことでルックアヘッドを防止しています。
- ETL は冪等性に配慮（ON CONFLICT DO UPDATE）しているため再実行で既存データを上書きしますが、運用前にバックアップ/検証を行ってください。
- 本リポジトリには実際の発注ロジック（証券会社への送信）や本番環境での動作保証は含まれていません。live モードでの自動発注は十分な検証後に有効化してください（KABUSYS_ENV=live）。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py: パッケージ初期化、バージョン
  - config.py: 環境変数読み込み・Settings（設定）管理
  - ai/
    - __init__.py
    - news_nlp.py: ニュースの銘柄別 NLP スコアリング（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py: マクロニュース + ETF MA200 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（fetch/save 含む）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - etl.py: ETLResult 再エクスポート
    - news_collector.py: RSS フィード取得・前処理・raw_news 保存
    - calendar_management.py: 市場カレンダー管理・営業日判定・カレンダー更新ジョブ
    - stats.py: zscore_normalize 等統計ユーティリティ
    - quality.py: データ品質チェック（missing/spike/duplicates/date consistency）
    - audit.py: 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py: momentum/value/volatility ファクター計算
    - feature_exploration.py: forward returns, IC, factor summary, rank 等
  - ai、data、research などの各モジュールは Docstring とロギングで設計方針が記載されています

---

## ログ / モニタリング

- ログレベル: 環境変数 `LOG_LEVEL` で制御（デフォルト INFO）
- 監視関連設定（PID ファイル、kill フラグ、CPU/MEM/DISK 閾値）は Settings 経由で取得可能（例: PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等）

---

## 開発者向けメモ

- テスト時には OpenAI / J-Quants の外部呼び出しをモックする設計になっています（各モジュール内の `_call_openai_api` や jquants_client._request をパッチ可能）。
- DuckDB の executemany に空リストを渡すことが問題になるバージョン向けに防御済み（params が空でないことを確認）。
- JSON レスポンスの耐障害性（余計な前後テキストの復元など）や API の 5xx/429 時の指数バックオフ等、実運用を想定した堅牢化がされています。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスや貢献方法、Issue / PR の流れなどを追記してください）

---

必要に応じて README に実行スクリプト（cron / systemd / Airflow など）や更に詳細な .env.example、マイグレーション／スキーマ初期化コマンドを追加できます。必要ならテンプレートや実行例を追記しますので教えてください。