# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants・RSS・OpenAI 等を組み合わせてデータ収集（ETL）、品質チェック、ニュースセンチメント解析、マーケットレジーム判定、ファクター計算、監査ログ管理までを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない箇所が多い）
- DuckDB を中心としたローカルデータレイヤー
- 冪等性（ETL / 保存は ON CONFLICT を利用）
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を実装
- OpenAI（gpt-4o-mini 等）を使った JSON Mode による NLP 評価

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート基準）
  - 必須環境変数チェック（Settings）
- データ収集（J-Quants）
  - 株価日足（OHLCV）取得と保存
  - 財務データ取得と保存
  - JPX マーケットカレンダー取得と保存
  - レート制御・認証トークン自動リフレッシュ・リトライ実装
- ETL パイプライン
  - 差分取得 / バックフィル / 品質チェック（missing/spike/duplicates/日付不整合）
  - 日次 ETL エントリ関数（run_daily_etl）
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP
  - 銘柄ごとにニュースをまとめて LLM に送信 → ai_scores テーブルへ保存（score_news）
  - バッチ処理・JSON レスポンスバリデーション・リトライ
- レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュースセンチメントを合成して市場レジームを判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリ
  - Z-score 正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions テーブルとインデックス
  - 初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## セットアップ手順

想定環境：Python 3.10+（typing の union 型等を利用）。必要な外部ライブラリの代表例を以下に示します。実際の requirements.txt はプロジェクトで管理してください。

推奨手順（例）:

1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

3. ソースをインストール（開発モード）
   - pip install -e .

4. 環境変数を設定
   - ルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に検出）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
- DUCKDB_PATH（省略可） — デフォルト: data/kabusys.duckdb
- SQLITE_PATH（省略可） — 監視用途などに: data/monitoring.db
- KABUSYS_ENV（省略可） — development / paper_trading / live（デフォルト development）
- LOG_LEVEL（省略可） — DEBUG / INFO / WARNING / ERROR / CRITICAL

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な例）

以下は Python REPL / スクリプトでの利用例です。DuckDB 接続は本プロジェクトの設定に従って `settings.duckdb_path` を使うのが便利です。

1. DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメントを計算して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

3. 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4. 研究用ファクターを計算する
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

5. 監査ログ用 DB 初期化（監査専用 DB を起動）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンに設定されます
```

注意点:
- OpenAI 呼び出しは外部 API を叩くため、テスト時は各モジュールの `_call_openai_api` をモックすることが想定されています。
- ETL や API 呼び出しは例外処理や再試行ロジックを内包していますが、API キーやネットワーク等の設定は事前に用意してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に実装されています。重要なモジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 収集（fetch_rss 等）
    - quality.py             — データ品質チェック（run_all_checks 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py — 市場カレンダー管理
    - audit.py               — 監査ログテーブル定義 / 初期化
    - (その他 jquants_client に紐づく save_* / fetch_*)
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / rank / factor_summary
  - ai/、data/、research/ などの下に小さなユーティリティ関数群が実装されています。

---

## 開発・運用上の注記

- .env 自動読込:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env`、`.env.local` を自動読み込みします。
  - 優先順位: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - テストや明示的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- OpenAI のエラー取り扱い:
  - rate limit / network / 5xx はリトライ（指数バックオフ）
  - エラー時はフェイルセーフとして一部モジュールは中立スコア（0.0 等）で継続します
- DuckDB 仕様注意:
  - 一部コードは DuckDB の executemany の特性（空リスト不可など）を考慮しています
- セキュリティ:
  - RSS 取得で SSRF 対策（リダイレクト時のホストチェック / private IP チェック / スキーム制限）
  - defusedxml を使用して XML インジェクションを防止

---

この README はコードベースの概要と基本的な利用方法にフォーカスしています。より詳細な設計文書（DataPlatform.md / StrategyModel.md 相当）や実運用手順があれば、それらと合わせてご利用ください。必要であれば README にコマンドライン例や CI / DB マイグレーション、監視設定などの追加セクションを追記します。