# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants / JPX のデータ取得、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注／約定追跡）などを含むモジュール群を提供します。

---

## 主な特徴（概要）

- J-Quants API クライアント（差分取得・ページネーション・リトライ・レート制御・トークン自動更新）
- ETL パイプライン（株価・財務・市場カレンダーの差分取得・保存・品質チェック）
- ニュース収集（RSS → raw_news、SSRF 対策・正規化・冪等保存）
- ニュース NLP（OpenAI を用いたバッチセンチメント評価、銘柄別 ai_scores 保存）
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を重み合成）
- ファクター計算・特徴量解析（モメンタム / バリュー / ボラティリティ、将来リターン・IC 等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → executions をトレースする監査スキーマ）
- DuckDB を主ストレージとして利用（軽量で高速な分析向け組み込み DB）

---

## 依存・動作環境

- Python 3.10+
- 必要な主要ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセスが必要（J-Quants / OpenAI / RSS）

pip でインストールする一例:
```bash
python -m pip install -r requirements.txt
# または開発時
python -m pip install -e .
```
（requirements.txt はプロジェクトに合わせて用意してください）

---

## 環境変数（主要）

設定は .env / .env.local / OS 環境変数から読み込まれます（優先順位: OS > .env.local > .env）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須（config.Settings で _require される項目）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

OpenAI 関連:
- OPENAI_API_KEY — AI モジュール（news_nlp / regime_detector）で使用（引数で上書き可）

オプション / デフォルト:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live; デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト: INFO)

例 .env（必要最小限）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを準備
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール（duckdb, openai, defusedxml 等）
4. 必要な環境変数を .env に記載（README 上の必須項目を参照）
5. DuckDB ファイルの親ディレクトリを作成（自動で作られる関数もありますが確認推奨）
6. ETL を実行してデータを初期ロード

---

## 使い方（主要な例）

- 設定読み込み:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作成して日次 ETL を走らせる:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（news_nlp）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数でセットしている場合、第3引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"Scores written: {n_written}")
```

- マーケットレジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または引数で指定
```

- 監査ログ DB を初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルに書き込みなどを行う
```

- 研究用ファクター計算:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書のリスト
```

注意点:
- ほとんどの関数はルックアヘッドバイアスを避けるために内部で date.today() を直接使わず、明示的な target_date を受け取ります。バックテスト等の際は target_date を厳密に指定してください。
- OpenAI 呼び出しはネットワークエラー等で失敗した場合フォールバックやスキップを行う設計です（例外が必ず上がるとは限りません）。ログを確認してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と Settings を提供（自動 .env ロード機能あり）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースのバッチセンチメント評価（OpenAI）
    - regime_detector.py — マーケットレジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch/save 関数）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETL インターフェース（ETLResult の再エクスポート）
    - news_collector.py  — RSS 取得・前処理・raw_news 保存
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - quality.py         — データ品質チェック（欠損・スパイク・重複・日付整合）
    - stats.py           — 統計ユーティリティ（z-score 正規化 等）
    - audit.py           — 監査ログスキーマ初期化 / init 関数
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー 等

---

## 注意事項 / 運用上のヒント

- DuckDB のバージョン互換性や executemany の空リスト制約など実装依存箇所があるため、ローカルでのテスト時は同等バージョンの duckdb を使ってください。
- J-Quants のレート制限（120 req/min）にあわせた RateLimiter を組み込んでいますが、大量一括取得の際は API トークンや利用制限に注意してください。
- OpenAI 呼び出しはコストが発生します。テスト時は API 呼び出しをモックするか、API キーを与えずに動作確認してください。
- .env.local をプロジェクトルートに置くとローカル上書きが可能です（自動ロード順: .env → .env.local 上書き）。

---

問題報告・貢献:
- バグや改善提案はリポジトリの Issue に記載してください。テストや小規模修正は PR を歓迎します。

以上がプロジェクトの README です。追加でサンプルスクリプトや .env.example を作成したい場合は、お手伝いします。