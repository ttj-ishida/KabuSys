# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI 経由）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）など、バックテスト・運用に必要なユーティリティを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（.env）例
- 基本的な使い方（コード例）
  - DuckDB 接続の作成
  - 日次 ETL 実行
  - ニューススコアリング（AI）
  - 市場レジーム判定
  - 監査ログスキーマ初期化
  - 研究用ファクター計算
- 自動 .env ロードの挙動
- ディレクトリ構成（主要ファイル説明）
- トラブルシューティング（よくある問題）

---

## プロジェクト概要

KabuSys は日本株データパイプラインと自動売買プラットフォームの基盤ライブラリです。J-Quants API からのデータ収集、DuckDB を用いたデータ格納、ニュースの収集と LLM によるスコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）などを包含します。  
本リポジトリはライブラリ群として提供され、他のアプリ／運用スクリプトからインポートして利用します。

---

## 主な機能

- J-Quants API クライアント（差分取得・ページネーション・自動リフレッシュ・レート制限・保存関数）
- ETL パイプライン（run_daily_etl）：カレンダー・株価・財務データの差分取得と品質チェック
- 市場カレンダー管理（営業日判定、next/prev trading day 等）
- ニュース収集（RSS、SSRF 対策、正規化、raw_news 保存）
- ニュース NLP（OpenAI を用いた銘柄別センチメント、ai_scores 保存）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの組合せ）
- 研究用モジュール（ファクター計算、将来リターン、IC、Z-score 正規化 等）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- 監査ログ（signal_events / order_requests / executions の DDL と初期化ユーティリティ）
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## 前提条件

- Python 3.10 以上（typing の新記法などを使用）
- 必要パッケージ（例）:
  - duckdb
  - openai (v1 の SDK 想定)
  - defusedxml
  - その他標準ライブラリ

パッケージは環境に合わせて requirements.txt を作成してインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリを取得してインストール（開発形態）
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```

2. 必要ライブラリをインストール（上の前提参照）

3. 環境変数を用意する（.env / .env.local）
   - 下記「環境変数（.env）例」を参照してください。

4. DuckDB データベースを作成（任意の場所にファイル）
   - デフォルトは data/kabusys.duckdb（settings.duckdb_path）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 環境変数（.env）例

KabuSys はプロジェクトルートの .env / .env.local を自動でロードします（詳細は下部参照）。主に次の環境変数を利用します。

必須:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- OPENAI_API_KEY=...  （ニュース NLP / レジーム判定で使用）

任意（デフォルト値あり）:
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development  # development|paper_trading|live
- LOG_LEVEL=INFO

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

環境変数が足りないと Settings のプロパティ呼び出し時に ValueError が発生します。

---

## 使い方（コード例）

以下は典型的な利用例です。DuckDB 接続は duckdb.connect(...) で取得し、各モジュール関数に渡します。

- DuckDB 接続作成:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニューススコアリング（OpenAI を用いる）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーは OPENAI_API_KEY 環境変数か、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（既存 DB に追加）:
```python
from kabusys.data.audit import init_audit_schema
# conn は DuckDB 接続
init_audit_schema(conn, transactional=True)
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- Z スコア正規化ユーティリティ:
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 自動 .env ロードの挙動

- パッケージ初期化時（kabusys.config の読み込み時）に、プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探し、見つかれば以下の順でロードします:
  1. .env  (override=False : OS 環境変数を上書きしない)
  2. .env.local (override=True : .env より優先。ただし OS 環境変数は保護)

- 自動ロードを無効化するには環境変数を設定します:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- .env のパースは Bash 風の "KEY=val", "export KEY=val", シングル/ダブルクォート、インラインコメントに対応しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス（アプリ設定）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM スコアリング（ai_scores 書込）
    - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存関数）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py  — RSS 取得・前処理・raw_news 保存
    - quality.py         — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py           — 汎用統計（zscore_normalize）
    - audit.py           — 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー 等

各モジュールには関数ドキュメントと設計方針が詳細にコメントとして含まれており、内部実装・使用上の注意が明記されています。

---

## トラブルシューティング（よくある問題）

- 環境変数不足により ValueError が発生する:
  - settings のプロパティ（例: settings.jquants_refresh_token）が呼ばれると必須 env が無ければ例外になります。.env を確認してください。

- OpenAI API 呼び出し失敗:
  - OPENAI_API_KEY が設定されているか確認。エラーはフェイルセーフでスコアを 0 にして継続する実装箇所が多いですが、レート制限や API 異常時はログを確認してください。

- DuckDB の操作で executemany に空リストを渡すと一部バージョンでエラー:
  - 実装上は空リスト渡しを回避するチェックがありますが、独自コードを追加する際は注意してください。

- RSS 取得で SSRF / プライベートアドレスブロック:
  - news_collector は内部アドレスや不正なスキームを防ぐ設計です。社内ネットワークやプロキシ経由でのアクセスが必要な環境では設定変更が必要になる場合があります。

---

必要があれば README にセットアップスクリプト、requirements.txt、サンプル .env.example を追加できます。特定の機能（例: ETL の cron 化、Slack 通知の統合、kabu API 実行例）について詳しいドキュメントを作成することも可能です。どの部分を優先して拡張しますか？