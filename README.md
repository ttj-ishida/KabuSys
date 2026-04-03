# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabu ステーション / OpenAI（LLM）を組み合わせて
ETL、ニュースセンチメント、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ等を提供します。

主な用途:
- J-Quants からの株価・財務・カレンダーの差分ETL
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント解析（ai_score）
- 市場レジーム（bull/neutral/bear）の日次判定（MA + LLM 合成）
- 研究向けファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → executions）のスキーマ初期化

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、raw_news 保存）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント解析（score_news: 銘柄別 ai_scores への保存）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 乖離とマクロニュースを合成）
  - 両モジュールは OpenAI（gpt-4o-mini）を JSON mode で利用、リトライ / フェイルセーフを備える
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・統計（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理
  - 環境変数・.env 自動ロード（プロジェクトルート検出、.env → .env.local、OS 環境優先）
  - settings オブジェクト経由で各種パラメータ取得（例: settings.jquants_refresh_token）

---

## 要件（例）

- Python 3.10+
- duckdb
- openai
- defusedxml
- そのほか urllib / 標準ライブラリ

（パッケージ化時は requirements.txt / setup.cfg にまとめることを想定）

最低限インストール例:
```
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

このライブラリは環境変数から設定を読み込みます。プロジェクトルートに `.env` / `.env.local` があれば自動的に読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須/任意）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD (必須)  
  kabu ステーション API のパスワード

- OPENAI_API_KEY (必須 for AI 機能)  
  OpenAI API キー（score_news / score_regime 実行時に必要）

- LINE_CHANNEL_ACCESS_TOKEN (任意)  
  LINE 通知に使用する場合のアクセストークン

- DUCKDB_PATH (任意) デフォルト: data/kabusys.duckdb  
- SQLITE_PATH (任意) デフォルト: data/monitoring.db

- PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視系の設定

サンプル `.env`（README 用例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

settings オブジェクト例:
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path("data/kabusys.duckdb")
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 環境を用意（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 必要パッケージをインストール
   ```
   pip install -e .            # パッケージ化されている場合
   # または最低限:
   pip install duckdb openai defusedxml
   ```
4. `.env` をプロジェクトルートに作成（上記サンプル参照）
5. DuckDB ファイルの格納ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（例）

以下は主要ユースケースの簡単な使用例です。これらはライブラリを直接インポートして実行します。

- DuckDB 接続を作る:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日が対象
print(result.to_dict())
```

- ニューススコアリング（score_news）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# target_date に対するニュースウィンドウ（前日15:00JST～当日08:30JST）を対象にする
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {count}")
```

- 市場レジーム判定（score_regime）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル（signal_events, order_requests, executions）が作成される
```

- 研究用ファクター計算:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- score_news / score_regime は OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要です。
- J-Quants 関連 API は JQUANTS_REFRESH_TOKEN が必要です。jquants_client はトークン自動リフレッシュやレート制御を備えています。

---

## セキュリティ・設計上の注意点

- news_collector は SSRF 防止（URL スキーム検証・プライベートIP 検査・リダイレクト検査）および XML パースに defusedxml を使用。
- jquants_client はトークン自動リフレッシュ（401 時）と指数バックオフ、固定間隔レートリミッタを実装。
- AI 関連はレスポンスの妥当性検証やリトライ処理、API 失敗時のフェイルセーフ（デフォルトは中立 0.0）を行います。
- .env の自動読み込みはプロジェクトルート判定を行い、CWD に依存しない実装です。自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / settings 管理（.env 自動読込）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメントの集約・API 呼び出し・ai_scores 書込み
    - regime_detector.py    — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 他）
    - calendar_management.py — マーケットカレンダーの管理（is_trading_day 等）
    - news_collector.py    — RSS 取得・前処理・raw_news 保存（SSRF 対策）
    - quality.py           — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py             — zscore_normalize 等
    - audit.py             — 監査ログテーブル定義・初期化
    - etl.py               — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py   — momentum/value/volatility ファクター
    - feature_exploration.py — forward returns / IC / summary
  - research/*, ai/* などの追加モジュール

---

## 補足 / 開発者向けメモ

- DuckDB を使用しているため、ローカルファイル（data/*.duckdb）で操作可能。`:memory:` を指定すればインメモリ DB になります。
- OpenAI 呼び出しは JSON mode を使って厳密な JSON を期待しますが、万が一余計な前後テキストが混入した場合の復元ロジックも含んでいます。
- テスト時には内部の API 呼び出し部分（_call_openai_api, _urlopen 等）をモックすることを想定した設計です。
- ETL や AI 実行はルックアヘッドバイアスを避けるため、内部で datetime.today() / date.today() を直接参照しない設計になっています（target_date を明示的に渡すこと推奨）。
- ロギングは各モジュールで logger = logging.getLogger(__name__) を使っています。運用時はハンドラを設定してください。

---

必要であれば、README にサンプル SQL スキーマ、より詳細な設定例や実行スクリプト（systemd / cron / Airflow など）例も追加できます。どの部分を詳しく載せたいか教えてください。