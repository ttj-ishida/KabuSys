# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）→ データ品質チェック → ニュースのNLPスコアリング → 市場レジーム判定 → 研究用ファクター計算 / 監査ログなど、トレードシステムのコアとなる機能群を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない設計が多く採用されています）
- DuckDB を主要なローカルDBとして利用（軽量かつ高速）
- J-Quants / OpenAI など外部APIはリトライやレート制御を備え堅牢に実装
- ETL / 品質チェックは失敗しても他処理を継続する（全体収集型のエラー処理）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（必要に応じて無効化可能）
  - 必須設定の取得・検証を提供（kabusys.config.settings）
- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（取得／保存／ページネーション対応／トークン自動リフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day 等）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS 取得／前処理／raw_news への冪等保存）
  - 監査ログ（signal_events / order_requests / executions テーブルの初期化・ユーティリティ）
- AI（kabusys.ai）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を利用、JSON Mode 経由）
  - マクロセンチメント + ETF MA を使った市場レジーム判定（bull / neutral / bear）
- 研究（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）

---

## 必要条件

- Python 3.10+（typing の構文などの都合上）
- 主要依存ライブラリ（最小）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに応じて追加の依存がある場合があります。pip install 時に適宜インストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

もしパッケージ配布（pyproject.toml / setup.py）がある場合は:
```
pip install -e .
```

---

## 環境変数 / .env

自動的に読み込まれる環境変数（プロジェクトルートに `.git` または `pyproject.toml` がある場合）:

必須（アプリケーション実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack のチャンネル ID

任意（デフォルト値あり/挙動制御）:
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（AI スコア処理で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env の自動読み込みを無効化

設定は `.env` / `.env.local` に記述できます。`.env.local` は `.env` の上書き（優先）です。自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル（.env.example として作る想定）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （必要に応じて他のライブラリも追加してください）
4. `.env` を用意して必須変数を設定（または環境変数をエクスポート）
5. DuckDB を使う場合、データディレクトリを作成（デフォルト `data/`）
   ```
   mkdir -p data
   ```
6. （任意）監査DBの初期化
   - 監査用 DuckDB を初期化する例は下記「使い方」を参照

---

## 使い方（代表的な API 呼び出し例）

以下の例は Python REPL やスクリプトから利用する想定です。

- 共通: settings を使ってパスや設定を取得
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（J-Quants から差分取得して保存、品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの計算（ai -> ai_scores テーブルへ書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote {n_written} scores")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用DBの初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# init_audit_db はスキーマ（signal_events / order_requests / executions）を作成します
```

- 研究モジュール（ファクター計算）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- カレンダー関連ユーティリティ
```python
from datetime import date
from kabusys.data import calendar_management as cal

is_trading = cal.is_trading_day(conn, date(2026, 3, 20))
next_td = cal.next_trading_day(conn, date(2026, 3, 19))
tds = cal.get_trading_days(conn, date(2026, 3, 1), date(2026, 3, 31))
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を前提としたプロンプト / JSON Mode を利用しており、API レスポンスのバリデートロジックが含まれます。OPENAI_API_KEY を環境変数に設定してください（または各関数に api_key を渡す）。
- J-Quants API はレート制限やトークンリフレッシュを内包します。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- 日付やウィンドウ計算は UTC / JST の扱いに注意（モジュール内で意図的に UTC naive datetime を使う箇所があります）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースのNLPスコアリング（OpenAI）
    - regime_detector.py            — マクロ+MAで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント / DB保存ユーティリティ
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - calendar_management.py        — マーケットカレンダー管理（営業日判定等）
    - news_collector.py             — RSS 取得・正規化・保存
    - quality.py                    — データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
    - audit.py                      — 監査ログテーブル初期化 / audit DB ユーティリティ
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー等
  - ai, research, data パッケージはそれぞれの公開 API を __all__ で管理

---

## 注意事項 / トラブルシューティング

- 自動で .env を読み込む仕組みがあるため、テストや CI で環境をコントロールしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境変数を注入してください。
- DuckDB に対する executemany の空リストバインドなど、DuckDB のバージョン依存の注意点があります。DuckDB のバージョンを合わせることで回避できる場合があります。
- OpenAI / J-Quants の API エラーは内部でリトライやフォールバック（zero/skip）を行いますが、キー未設定では ValueError が発生します。必ず API キーを用意してください。
- news_collector は RSS を解析するために defusedxml を使用しています。RSS の不正な XML や巨大なレスポンスは安全策でスキップされます。

---

## 貢献

バグ報告・機能改善やテストの追加は歓迎します。Pull Request 前に Issues で議論してください。

---

以上がこのコードベースの概要と利用方法です。必要であれば README に具体的な .env.example、requirements.txt、そしてサンプルのスクリプト（run_etl.py 等）を追加するテンプレートも作成できます。どのフォーマットを優先して出力するか指示してください。