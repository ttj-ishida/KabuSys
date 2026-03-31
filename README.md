# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（データパイプライン・リサーチ・AI/NLP・監査ログを含む）を提供するコードベースです。J-Quants / kabu ステーション / OpenAI を利用し、ETL、ニュースセンチメント、ファクター計算、監査ログ、マーケットカレンダー管理などを実装しています。

## 主な特徴（機能一覧）
- データ収集（J-Quants API 経由）
  - 株価日足（OHLCV）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS）および前処理（SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF とマクロニュースの組合せで bull/neutral/bear を判定）
- ファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（signal → order_request → execution のトレーサビリティを担保）
- DuckDB ベースの永続化（冪等保存、ON CONFLICT を利用）
- 設定管理（.env 自動読み込み、環境変数ベース）

## 必要条件
- Python 3.10+
- ネットワーク接続（J-Quants API、OpenAI、RSSソース）
- ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ: urllib 等を多用）

必要なパッケージはプロジェクトに requirements.txt が無ければ次のようにインストールできます（例）:
```bash
python -m pip install duckdb openai defusedxml
```

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-root>
```

2. 仮想環境を作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
```

3. 必要パッケージをインストール
```bash
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
# その他プロジェクトで必要なパッケージがあれば追加してください
```

4. 環境変数の設定
- プロジェクトルートに `.env` / `.env.local` を配置すると、モジュール起動時に自動で読み込まれます（config モジュールの自動読み込み機能）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例として必要な主要環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能利用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）データベースパス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT などの監視設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

（.env.example を参考に .env を作成してください）

## 使い方（代表的な例）

以下は Python から直接呼び出す例です。プロジェクトをパッケージとしてインポートできるように PYTHONPATH を設定してください（例: src を追加）。

例: DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DuckDB ファイルに接続
conn = duckdb.connect(str(settings.duckdb_path))

# ETL 実行（target_date を指定しないと今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

例: ニュース NLP（銘柄別スコア取得）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("<path-to-duckdb>"))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"書き込んだ銘柄数: {n_written}")
```

例: 市場レジーム評価
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str("<path-to-duckdb>"))
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

例: 監査用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス・クエリ可能
```

例: J-Quants 生データ取得（直接呼び出し）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

注意点:
- AI（OpenAI）呼び出しは API キーを環境変数 OPENAI_API_KEY に設定するか、各関数の api_key 引数で渡してください。
- ニュース収集は外部 RSS を取得するためネットワークに依存します。SSRF 対策やサイズ制限が組み込まれています。
- 多くの操作は DuckDB 接続を直接受け取る設計です。接続は呼び出し元で管理してください。

## 設定管理のポイント
- config.Settings は環境変数を参照して各種パスやシークレットを提供します。
- .env / .env.local は自動でプロジェクトルート（.git または pyproject.toml を探索）から読み込まれます。
- テストなどで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py            - 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（取得 + 保存）
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - etl.py                        - ETL 公開インターフェース（ETLResult エクスポート）
    - quality.py                    - データ品質チェック
    - stats.py                      - 汎用統計ユーティリティ（zscore_normalize）
    - news_collector.py             - RSS ニュース収集（SSRF対策・前処理）
    - calendar_management.py        - マーケットカレンダー管理（営業日判定等）
    - audit.py                      - 監査ログ（監査テーブル作成）
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（momentum/value/volatility）
    - feature_exploration.py        - 将来リターン計算・IC・統計サマリー

## 開発・テストのヒント
- OpenAI 呼び出しは各モジュール内で _call_openai_api がラップされています。ユニットテストではこれをモックして API 呼び出しを差し替えられます。
- DuckDB を使うためテストはインメモリ DB（":memory:"）で実行できます（data.audit.init_audit_db の引数に ":memory:" を指定）。
- config モジュールはプロジェクトルート探索して .env を自動読み込みするため、テスト時に環境変数を一時的にセットするか `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- ロギングは各モジュールで logger を使用しています。テストではログレベルを DEBUG に設定すると詳細が見えます。

## 運用上の注意
- J-Quants の API レート制限や OpenAI のレート制限を考慮して実行スケジュールを設計してください（jquants_client は固定間隔スロットリング等を実装）。
- 本番（live）モードでは KABUSYS_ENV を `live` に設定し、発注・実行周りの設定（kabu ステーション等）を慎重に管理してください。
- 監査ログは削除しない前提で設計されています。監査テーブルはトレーサビリティ確保のため慎重に管理してください。

## ライセンス
- この README はリポジトリのコード構成に基づく説明です。実際のライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください。

---

必要があれば README に含める具体的な .env.example のテンプレート、より詳細な CLI 実行例、または各モジュールごとの API 使用例（関数引数・戻り値の詳細）を追加で作成します。どの情報を優先して欲しいか教えてください。