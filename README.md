# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリです。  
J-Quants / RSS / OpenAI（LLM）等の外部データを取得・加工し、DuckDB を用いた ETL、ニュース NLP、マーケットレジーム判定、ファクター算出、監査ログスキーマなどのユーティリティを提供します。

---

## 主な特徴（機能一覧）

- データ収集・ETL
  - J-Quants API からの日次株価（OHLCV）・財務データ・JPX カレンダーの差分取得（ページネーション・リトライ・レート制御）
  - RSS からのニュース収集（SSRF対策、トラッキングパラメータ除去、前処理、冪等保存）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE 等）

- データ品質チェック
  - 欠損、主キー重複、スパイク（前日比急変）、将来日付／非営業日データ検出

- ニュース NLP / LLM
  - 銘柄ごとのニュースをまとめて OpenAI に送信しセンチメント（ai_score）を算出して保存（JSON Mode を利用）
  - エラーハンドリング・リトライ・バッチ処理対応

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成し、日次のレジーム（bull/neutral/bear）を判定して保存

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ

- 監査（トレーサビリティ）
  - シグナル → 発注要求 → 約定までトレースする監査テーブル定義と初期化ユーティリティ（DuckDB）

- 設定管理
  - .env（および .env.local）または環境変数から設定値を自動読み込み（プロジェクトルート自動検出）。自動ロードを無効化するオプションあり。

---

## セットアップ

前提
- Python 3.10 以上（*本リポジトリはモダンな型ヒント・構文を利用しています。3.11 を推奨*）
- DuckDB と OpenAI SDK、defusedxml 等の依存ライブラリ

例: 仮想環境作成・依存導入（pip）
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 必要に応じて他のライブラリを追加してください
# 例: requests 等（本コードベースは標準ライブラリの urllib を多用）
```

パッケージとしてインストール（開発モード）
```bash
pip install -e .
```
（プロジェクトに setup.cfg/pyproject.toml があれば上記で開発インストール可能です）

---

## 環境変数（主なもの）

このパッケージは .env/.env.local を自動読み込みします（読み込み優先順: OS 環境変数 ＞ .env.local ＞ .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（使用する機能によっては未設定でも可）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL／jquants_client）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等）
- SLACK_BOT_TOKEN: Slack 通知用（もし Slack 機能を使うなら）
- SLACK_CHANNEL_ID: Slack チャネル ID
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系）

オプション（デフォルトあり）:
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等（監視関連）

.env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=CXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な呼び出し例）

以下はライブラリを直接利用する際の簡単なサンプルです。基本的に DuckDB 接続を渡して各処理を実行します。

1) DuckDB 接続を作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLU（銘柄ごとの ai_scores 計算）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示するか、環境変数 OPENAI_API_KEY を設定
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ用 DB 初期化（監査専用の DuckDB ファイルを作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセス・書き込みが可能
```

6) 研究用: ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
volatility = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意点:
- いずれの関数も内部で「datetime.today()」や「date.today()」を参照しない設計（Look-ahead bias を避ける）です。必ず target_date を明示してください。
- OpenAI / J-Quants の API はキー・トークンが必要です。環境変数から自動的に読み込まれますが、関数引数で明示的に渡すこともできます。
- DuckDB に必要なテーブルスキーマは ETL / schema 初期化処理や別途用意するスクリプトで準備してください（本 README はスキーマ初期化スクリプトを含みません）。

---

## ディレクトリ構成（主要ファイルの説明）

（パッケージルート: src/kabusys/）

- __init__.py
  - パッケージのバージョンと公開サブモジュールを定義。

- config.py
  - 環境変数の自動読み込み（.env / .env.local）、設定オブジェクト settings を提供。

- ai/
  - news_nlp.py: ニュースのセンチメント算出（OpenAI を用いたバッチ処理、バリデーション、DuckDB への書き込み）
  - regime_detector.py: ETF 200 日 MA 乖離とマクロニュースセンチメントを合成して市場レジーム判定
  - __init__.py: API の公開（score_news, score_regime 等）

- data/
  - jquants_client.py: J-Quants API クライアント（認証、レート制御、リトライ、DuckDB への保存関数含む）
  - pipeline.py: ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等）
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 取得と前処理、raw_news への保存処理（SSRF 対策等）
  - calendar_management.py: market_calendar の CRUD・営業日判定ユーティリティ（is_trading_day, next_trading_day 等）
  - quality.py: 品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログスキーマ定義・初期化（signal_events, order_requests, executions）

- research/
  - factor_research.py: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC（スピアマン）、統計サマリー、ランク化
  - __init__.py: 研究機能の公開 API（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）

---

## 運用上の注意 / トラブルシューティング

- .env 自動読み込み:
  - パッケージは実行時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して .env / .env.local を読み込みます。テスト時や明示的に読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 読み込み順序: OS 環境変数 ＞ .env.local（上書き） ＞ .env（未設定キーのみセット）。

- API レート制御・再試行:
  - J-Quants クライアントは 120 req/min に合わせて内部的に待機します。大量データ取得時は処理時間がかかります。
  - OpenAI 呼び出しは JSON Mode を利用し、429 / ネットワークエラー / タイムアウト / 5xx を対象に指数バックオフでリトライされます。失敗時はフェイルセーフとしてスコアを 0.0 にフォールバックする設計の箇所もあります（処理の継続）。

- DuckDB の互換性:
  - 実行中の DuckDB バージョンによっては executemany に空リストを渡せないなどの挙動差分があります（pipeline.news などで対処済み）。問題があれば DuckDB のバージョンを確認してください。

- 時刻／タイムゾーン:
  - 監査ログは UTC にタイムゾーン固定して保存する設計です（init_audit_schema は SET TimeZone='UTC' を実行）。

---

この README はコードベースの主要な利用方法と設計意図を簡潔にまとめたものです。より詳細な設計仕様（DataPlatform.md / StrategyModel.md 等）やスキーマ定義、運用手順が別ドキュメントとして存在する場合はそちらを参照してください。必要であれば具体的なスキーマ定義や CLI 実行例、Docker コンテナ化手順も追加できます。