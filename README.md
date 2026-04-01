# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援機能を備えた自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター算出、監査ログ用スキーマなどを提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分で取得・保存
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL 実行結果を表す ETLResult

- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合の検出

- ニュース収集・NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、受信サイズ制御）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores）生成
  - マクロニュースを使った市場レジーム判定（bull/neutral/bear）

- リサーチユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
  - 監査用の DuckDB 初期化関数（UTC タイムゾーン固定）

- 設定管理
  - .env / 環境変数読み込み（プロジェクトルート検出、自動読み込み）
  - 必須設定は例外で通知

---

## 要求・依存

- Python 3.10 以上（型注釈や | None 構文を利用）
- 主な Python パッケージ
  - duckdb
  - openai (OpenAI SDK v1 系)
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

インストールは通常の pip 環境で行います（パッケージ名はプロジェクトに応じて設定してください）。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをローカルインストールする場合
pip install -e .
```

---

## 環境変数（.env の例）

config.Settings で参照される主な環境変数:

必須（アプリ動作に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / regime 判定で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行モジュール利用時）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト有り）
- KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — sqlite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

簡易 .env.example:
```
# .env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env 読み込みはデフォルトで有効です。無効化するには環境変数を設定:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージのインストール
   ```
   pip install duckdb openai defusedxml
   ```

   プロジェクト配布の要求ファイル（requirements.txt）があればそれを利用してください。

3. 環境変数を設定（.env をプロジェクトルートに配置）
4. DuckDB 用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（抜粋サンプル）

- 日次 ETL 実行（prices / financials / calendar を差分取得して保存）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl  # run_daily_etl を直接 import する形

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの取得（ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", written)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# 返された conn は DuckDB 接続
```

- ファクター計算・リサーチ関数
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
forward = calc_forward_returns(conn, target_date=date(2026,3,20))
# 例: IC 計算
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
```

注意:
- OpenAI を利用する関数は api_key 引数で明示的にキーを渡すことも可能です（テストや多キー運用に便利）。
- 関数は Look-ahead bias 防止の設計方針を採っており、内部で date.today() を不適切に参照しないように実装されています。必ず target_date を明示するのが推奨です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの NLP スコアリング（score_news）
    - regime_detector.py      — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save 関数）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS ニュース収集・前処理
    - calendar_management.py  — 市場カレンダーの管理・ユーティリティ
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Volatility/Value の算出
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - research/（他にファイルやユーティリティ）
  - （その他：strategy / execution / monitoring などの名前空間が __all__ に含まれる想定）

各モジュールはドキュメント文字列で設計方針・処理フローが明記されています。関数単位で引数・返り値の仕様が記載されているため、利用時は該当モジュールの docstring を参照してください。

---

## 開発・テスト時のヒント

- 自動的な .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト中に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしてください。
- OpenAI 呼び出しやネットワーク依存部分はモジュール内で _call_openai_api や _urlopen をラップしているため、ユニットテストではこれらをモックして外部通信を避けてください。
- DuckDB の executemany はバージョン差で挙動が異なるため、コード側で空パラメータのケースを明示的に避けています。テスト用 DB は ":memory:" で作成可能です。

---

必要であれば README を拡張して、具体的な ETL スケジュール例（cron / systemd タイマー）、Slack 通知のワークフロー、Strategy/Execution 層の利用例なども追加します。どの部分をさらに詳しくしたいか教えてください。