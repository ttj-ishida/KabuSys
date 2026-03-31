# KabuSys

KabuSys は日本株向けのデータプラットフォーム + 自動売買支援ライブラリです。J-Quants や RSS、OpenAI（LLM）などの外部データソースを取り込み、ETL、品質チェック、ニュース NLP、レジーム判定、ファクター計算、監査ログスキーマなどの機能を提供します。

主な利用ケース:
- 日次 ETL（株価・財務・市場カレンダー）の実行と品質チェック
- ニュース記事の収集と LLM による銘柄センチメント生成
- マクロニュースと移動平均乖離を使った市場レジーム判定
- 研究用途のファクター計算（モメンタム/バリュー/ボラティリティ等）
- 約定まで追跡可能な監査ログ（DuckDB）初期化

---

## 機能一覧

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
  - 必須環境変数を Settings クラス経由で取得

- データ ETL（J-Quants 連携）
  - 株価日足、財務データ、JPX カレンダーの差分取得（ページネーション対応）
  - レート制限管理、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損、重複、将来日付、スパイク検出などを実施し QualityIssue を返却

- ニュース収集・NLP
  - RSS からニュース取得（SSRF/サイズ/圧縮対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄センチメント（ai_scores）生成（バッチ処理・リトライ）
  - レスポンス検証と安全なフォールバック

- レジーム判定（市場センチメント）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM スコア（重み 30%）を合成
  - market_regime テーブルへ冪等書き込み

- 研究用モジュール
  - モメンタム / バリュー / ボラティリティ 等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ

- 監査（Audit）
  - signal_events / order_requests / executions を含む監査スキーマを DuckDB に初期化
  - init_audit_db / init_audit_schema を提供

---

## 前提・依存

- Python >= 3.10（Union 型表記 Path | None 等を使用）
- 必要な外部ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API, 各 RSS ソース, OpenAI API

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## 環境変数（主なもの）

以下は本パッケージで参照される主な環境変数です。`.env.example` を参照して `.env` を作成してください。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD : kabuステーション API パスワード（本コードベースで参照あり）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV : environment (development | paper_trading | live). デフォルト: development
- LOG_LEVEL : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL). デフォルト: INFO
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime の引数でも渡せます）

自動 .env 読み込み:
- パッケージ import 時、プロジェクトルート（.git または pyproject.toml があるフォルダ）から `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実運用では pyproject.toml / requirements.txt を使って依存を固定してください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必須変数を記載してください（例）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     ```
   - 自動ロードの動作は README 上部「環境変数」を参照。

5. DuckDB ファイル保存ディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python コード上（スクリプトや REPL）での呼び出し例です。実行前に必要な環境変数を設定してください。

共通: DuckDB 接続の取得例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象（環境に合わせて調整）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーを明示的に渡すことも可能（None なら環境変数 OPENAI_API_KEY を参照）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジームを判定して market_regime テーブルへ書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
# さらに z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログ用の DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# または既存 conn に対してスキーマを追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- ETL の個別ジョブ（例: 株価差分 ETL）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

---

## 注意点・設計上の留意事項

- ルックアヘッドバイアス防止:
  - 多くの関数は内部で date.today()/datetime.today() を参照せず、引数で target_date を受け取ります。
  - ETL と解析は明示的な日付を指定して使うことを推奨します。

- フォールバックとフェイルセーフ:
  - LLM 呼び出しや外部 API が失敗した場合、多くの箇所で安全側の値（例: 0.0）にフォールバックして継続します。ログで警告を確認してください。

- テストしやすさ:
  - OpenAI 呼び出しや HTTP のラッパー関数はモック差し替えできるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api, kabusys.data.news_collector._urlopen）。

- 環境変数の保護:
  - .env の自動読み込みは OS 環境変数を優先し、.env.local を上書きできる仕組みになっています。

---

## ディレクトリ構成

主要モジュールとファイル（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - etl.py                        — ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ初期化
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - news_collector.py             — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ

この README は主要なエントリポイントと使い方の概要を示しています。詳細な API の使用方法やパラメータは各モジュールの docstring を参照してください。

---

必要であれば、README に以下の情報も追加できます:
- CI / テストの実行方法（pytest 等）
- 開発用の pyproject.toml / requirements.txt のサンプル
- 運用ガイド（本番・ペーパートレード・Slack 通知設定）