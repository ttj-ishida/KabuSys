# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。J-Quants や RSS、OpenAI（LLM）を組み合わせてデータ取得、品質チェック、ニュース/NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レート制限・トークン自動リフレッシュ・リトライ処理実装
- ETL パイプライン
  - 差分取得、保存（DuckDB への冪等保存）、品質チェックを統合して日次ETLを実行
- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付整合性チェック（market_calendar ベース）
- ニュース収集 / NLP
  - RSS 収集（SSRF 対策・トラッキングパラメータ除去）、raw_news 保存
  - OpenAI を用いた銘柄別ニュースセンチメント（ai_scores へ保存）
  - レスポンスバリデーション・バッチ処理・リトライ
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（Audit）
  - signal → order_request → execution まで UUID ベースでトレース可能な監査テーブルを DuckDB に初期化・管理

---

## 必要条件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

依存はプロジェクトの pyproject.toml / requirements.txt に合わせてインストールしてください。簡易例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install duckdb openai defusedxml
```

（実プロジェクトでは pyproject.toml / requirements を参照してください）

---

## 環境変数（主要）

このプロジェクトは環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を読み込みます（自動ロードは .git または pyproject.toml を基準にプロジェクトルートを探索して行います）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（少なくとも開発で必要なもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文実行等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

オプション / デフォルト値あり:

- KABUSYS_ENV — {development|paper_trading|live}（default: development）
- LOG_LEVEL — {DEBUG|INFO|WARNING|ERROR|CRITICAL}（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（default: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID 保存先（default: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値

例 `.env`（簡易）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要なパッケージをインストール
   - プロジェクトに pyproject.toml / requirements がある場合はそちらを利用
   ```bash
   pip install -e .
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（.env をプロジェクトルートに作成するのが簡単）
   - 必要なキーを `.env` に記述（上記参照）

5. データディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単なコード例）

以下は主要なユースケースの最小例です。すべて DuckDB 接続（duckdb.connect）を渡して処理を行います。

- DuckDB 接続の作成（設定の DUCKDB_PATH を使用）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース（NLP）スコアリング（OpenAI が必要）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を利用
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

- 市場レジームスコア計算

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（監査専用の DuckDB を作る）

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査テーブルが初期化された接続
```

- ログレベル設定（アプリ起動側で行う例）

```python
import logging
logging.basicConfig(level=logging.INFO)
```

---

## よく使うモジュール / API の概要

- kabusys.config
  - settings: 環境変数ラッパー（例: settings.jquants_refresh_token）
  - 自動で .env / .env.local をプロジェクトルートから読み込み（無効化可）

- kabusys.data
  - jquants_client.py: J-Quants API からの取得・DuckDB への保存（fetch_*/save_*）
  - pipeline.py: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl と ETLResult
  - quality.py: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector.py: RSS 取得と raw_news への保存ロジック
  - audit.py: 監査テーブル DDL と初期化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント取得 → ai_scores へ保存
  - regime_detector.score_regime: ETF MA とニュースセンチメントを合成して market_regime 保存

- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - quality.py
  - stats.py
  - calendar_management.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/（研究・分析向けユーティリティ群）

（上は要点抜粋です。実際のファイルはさらに詳細なテスト・ユーティリティ等がある場合があります）

---

## 注意事項 / 実運用での考慮点

- OpenAI や J-Quants など外部 API 呼び出しはコストやレート制限に注意してください。テスト時は該当呼び出しをモックしてください（コード内でテスト用に差替え可能な実装あり）。
- DuckDB での executemany による空リストバインドの取り扱い（コメントに記載）など、バージョン互換性に依存する細かい挙動があります。DuckDB のバージョンに注意してください。
- Look-ahead bias を防ぐため、モジュールは target_date を明示して処理し、datetime.today()/date.today() を直接参照しない設計になっています（ただし run_daily_etl のデフォルトは today を使用します）。
- ニュース収集の SSRF 対策、サイズ制限、XML の安全パーサ defusedxml の利用などセキュリティに配慮した実装が含まれます。
- 本リポジトリの .env.example（なければ README のサンプルを利用）を参考に環境変数を整えてください。

---

ご要望があれば、README に次の追加を行えます:
- pyproject.toml / requirements の具体的なインストール手順
- よく使う CLI スクリプトのサンプル（cron / systemd 実行例）
- 実行例の詳細（ログ出力サンプル、エラー対処方法）
- 各テーブルスキーマの詳細ドキュメント

必要であればどれを追記するか教えてください。