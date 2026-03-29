# KabuSys

KabuSys は日本株のデータパイプライン、ニュース NLP、リサーチ、監査ログ、ETL を含む自動売買支援ライブラリです。J-Quants や kabu ステーション、OpenAI（LLM）など外部サービスと連携して、データ収集→品質チェック→ファクター計算→AI スコア付与→監査ログの流れを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を直接参照しない）
- DuckDB を中心とした軽量オンディスク DB
- API 呼び出しはリトライ・バックオフ・レート制御を実装
- 冪等性（ETL/保存処理は ON CONFLICT / DELETE→INSERT で上書き）
- フェイルセーフ（外部 API 失敗時はスキップ・デフォルト値で継続）

Version: 0.1.0

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動ロード（パッケージルート検知、自動保護）
  - 必須環境変数のチェック
- データ取得 / ETL（kabusys.data）
  - J-Quants からの株価・財務・市場カレンダー取得（ページネーション・レート制御）
  - 差分取得（最終取得日ベース）、バックフィル
  - raw_prices, raw_financials, market_calendar などへの冪等保存
  - ETL の統合エントリ（run_daily_etl）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS）と保存（SSRF 対策、トラッキング除去）
  - 監査ログスキーマ初期化 / 監査 DB（order_requests / executions / signal_events）
- AI（kabusys.ai）
  - ニュース NLP による銘柄ごとのセンチメントスコアリング（OpenAI gpt-4o-mini）
  - マクロニュースと ETF の MA200 乖離を合成した市場レジーム判定
  - API 呼び出しは JSON Mode を使用、再試行・パース保護実装
- リサーチ（kabusys.research）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- ヘルパー（logging 設定、DB 初期化など）

---

## 前提 / 必要環境

- Python 3.10+
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml
- （標準ライブラリ中心で外部依存は最小限ですが、OpenAI や duckdb, defusedxml は必要）

推奨パッケージ（examples）
- duckdb
- openai
- defusedxml

インストール例（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを開発モードでインストールする場合
pip install -e .
```

---

## 環境変数 / .env

自動ロード箇所（パッケージはプロジェクトルートを .git または pyproject.toml で検出）：
- OS 環境変数 > .env.local > .env（順に上書き）

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（実行モジュール用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知用チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使用する場合）

任意 / デフォルト:
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"
- KABUSYS_ENV: one of {"development", "paper_trading", "live"}（デフォルト development）
- LOG_LEVEL: one of {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}（デフォルト INFO）

簡易的な .env.example（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをチェックアウト
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール
   - 例: pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください
4. プロジェクトルートに .env を作成（.env.example を参照）
5. DuckDB の格納先ディレクトリを作る（必要に応じて）
   - 例: mkdir -p data
6. （初回）監査ログ DB を初期化（必要に応じて）
   - Python スクリプトから init_audit_db を呼ぶ（下参照）

---

## 使い方（サンプル）

すべての操作は Python から呼び出します。以下は主な API の使用例。

- ETL（日次 ETL を実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュース NLP スコア付与（ai.score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"書込み銘柄数: {n_written}")
```

- 市場レジーム評価（ai.regime_detector.score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルとインデックスが作成されます
```

- ファクター計算・リサーチ
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))

fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
```

- 設定（Settings）を直接参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 実装上の注意 / 設計メモ

- AI 呼び出しは gpt-4o-mini を想定（JSON Mode を使用）。レスポンスのパースに失敗した場合は安全に 0（中立）へフォールバックします。
- J-Quants クライアントは 120 req/min のレート制御、401 の自動リフレッシュ、ページネーション対応、リトライを実装しています。
- ETL は部分失敗に強く、各ステップで例外をキャッチしてログに残しつつ次工程へ進みます。最終的な ETLResult で品質問題やエラー状況を確認してください。
- ニュース収集は SSRF 対策（リダイレクト先検査・プライベート IP 検出）や受信サイズ制限、トラッキングパラメータ除去を行います。
- 自動環境変数ロードは .git または pyproject.toml を基準にプロジェクトルートを検出して .env / .env.local を読み込みます。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの概観（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                        -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py              -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（取得・保存）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETLResult 再エクスポート
    - news_collector.py               -- RSS ニュース収集
    - calendar_management.py          -- マーケットカレンダー管理 / 営業日判定
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                        -- 監査ログスキーマと初期化
  - research/
    - __init__.py
    - factor_research.py              -- Momentum / Value / Volatility 等
    - feature_exploration.py          -- 将来リターン / IC / summary / rank

（プロジェクトルート）
- .env (推奨)
- .env.local (ローカル上書き)
- data/ (デフォルト DB 保存先)
- src/

---

## FAQ / よくある質問

Q: OpenAI キーや J-Quants トークンはどの環境変数名ですか？
- OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN を使用します。config.Settings 経由で取得します。

Q: 自動で .env を読み込むのを止めたい
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: DuckDB ファイルを変更したい
- 環境変数 DUCKDB_PATH を設定してください（パスは expanduser() されます）。

Q: ライブ発注（実際の売買）はここに含まれますか？
- 本コードベースはデータパイプライン、リサーチ、監査ログ、AI スコアリングを提供します。実際の発注ロジック（証券会社との接続・注文フロー）は別モジュール（execution 等）で実装する想定です。KABU_API_PASSWORD や KABU_API_BASE_URL は kabu ステーションと連携するための準備変数です。

---

もし README に追加したいサンプルスクリプト、CI 設定、あるいはパッケージング手順（pyproject.toml / setup.cfg）などがあれば教えてください。必要に応じて README を拡張します。