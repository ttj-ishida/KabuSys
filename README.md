# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（注文→約定トレーサビリティ）などを包含します。

---

## 主要な特徴

- データ取得（J-Quants API）と冪等保存（DuckDB）
  - 日次株価（OHLCV）、財務データ、JPX カレンダー、上場銘柄情報取得
  - API レート制御・再試行・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックをまとめて実行
- ニュース収集・NLP（OpenAI）
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）
  - ニュースを銘柄毎にまとめて LLM でセンチメント算出（ai_scores）
  - 単体テストしやすい設計（API 呼び出しの差し替え可能）
- 市場レジーム判定（ETF + マクロニュースの LLM センチメントを合成）
- 研究（research）モジュール
  - モメンタム、バリュー、ボラティリティなどのファクター計算
  - 将来リターン・IC 計算・ファクターサマリ生成、Zスコア正規化
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal_events / order_requests / executions）を DuckDB に初期化・管理

---

## 環境変数（必須 / 推奨）

プロジェクトは環境変数 / .env から設定を読み込みます（自動ロード機能あり）。主なキー:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / regime の呼び出しで使用可能）

任意（デフォルトあり）:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視関連 SQLite パス（デフォルト: data/monitoring.db）

備考:
- .env / .env.local をプロジェクトルートから自動で読み込みます（CWD に依存しない探索ロジック）。
- 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 必要な環境・依存パッケージ

- Python 3.10 以上（型注釈や union 型表記を使用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

インストール例（仮想環境を推奨）:
```sh
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクトに requirements.txt / pyproject.toml を用意していればそちらを利用してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成して依存をインストール（上記参照）
3. プロジェクトルートに `.env` を用意（.env.example を参考に必須キーを設定）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     KABU_API_PASSWORD=yourpassword
     ```
4. DuckDB ファイルの準備（デフォルト `data/kabusys.duckdb`）
   - 初期スキーマが必要な場合は、関連モジュールで提供する初期化関数を実行してください（例: 監査ログ用 init_audit_db）。
5. （オプション）Kabu ステーションや Slack の設定を行う

---

## 使い方（サンプル）

以下は主要な操作の呼び方例です。実際はアプリの構成に合わせてスクリプト化してください。

- 設定の利用:
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続と ETL の実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数か api_key 引数で指定）:
```python
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数から自動取得
print(f"scored {count} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- 研究モジュールの使用例:
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
conn = duckdb.connect(str(settings.duckdb_path))
moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
normed = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

テストのヒント:
- OpenAI 呼び出しはモジュール内の `_call_openai_api` をモックして差し替えられるよう設計されています（例: unittest.mock.patch）。

---

## よく使う機能の注意点 / 設計方針（要点）

- 「ルックアヘッドバイアス」対策として、各モジュールは `datetime.today()` / `date.today()` を内部ループで無造作に参照しない設計です。外部から `target_date` を明示して呼び出すことを想定しています。
- ETL / 保存処理は冪等性を重視（ON CONFLICT DO UPDATE 等）しているため、繰り返し実行しても上書きで安全に更新できます。
- API 呼び出しはレート制御と指数バックオフを実装し、ネットワーク障害や 5xx 等に対処します。OpenAI 呼び出しもリトライとフェイルセーフ（失敗時は中立スコアを採用）を行います。
- ニュース収集は SSRF 対策・XML ハンドリングの安全化（defusedxml）・受信サイズ制限などを施して堅牢化しています。
- データ品質チェックは Fail-Fast ではなく、検出されたすべての Issue を返して呼び出し元で判断できるようになっています。

---

## ディレクトリ構成（抜粋）

プロジェクト主要ファイル/モジュールの構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメント生成 / OpenAI 連携
    - regime_detector.py               — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py           — マーケットカレンダー管理 + 営業日判定
    - etl.py (パイプライン公開)        — ETL エントリポイント（run_daily_etl 等）
    - pipeline.py                      — ETL 実装（run_prices_etl 等） & ETLResult
    - stats.py                         — 汎用統計（Zスコア正規化等）
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログテーブル初期化 / 管理
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - news_collector.py                — RSS 取得・記事前処理・raw_news 保存
    - etl.py / pipeline.py / …         — ETL 周りのロジック
  - research/
    - __init__.py
    - factor_research.py               — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py           — 将来リターン, IC, ファクターサマリ等

（上記は実装ファイルの主要な抜粋です。詳細はソースツリーを参照してください。）

---

## 開発 / テストに関する補足

- テスト時は環境変数自動読み込みを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- OpenAI や外部 API 呼び出しはモックしやすいように設計されています（内部の `_call_openai_api` を patch など）。
- DuckDB はファイルベース・インメモリ双方で利用できます（dbpath に `":memory:"` を指定）。

---

README はここまでです。追加で以下の内容が必要であれば教えてください:
- より詳細な .env.example（テンプレート）
- SQL スキーマ / 初期化スクリプト抜粋
- サンプル CLI スクリプト（ETL 起動 / ニュース収集 / レジーム判定 の cron 例）