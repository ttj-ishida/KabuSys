# KabuSys

日本株向けのデータプラットフォーム兼自動売買ライブラリ（モジュール群）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI 経由のセンチメント）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ管理などを提供します。

---

## 主な特徴（要点）

- ETL パイプライン
  - J-Quants API から株価（OHLCV）・財務・カレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・品質チェック機能を含む日次 ETL（run_daily_etl）
- ニュース収集と NLP
  - RSS フィード収集（SSRF 対策、URL 正規化、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（score_news）
  - マクロニュース＋ETF MA200乖離を合成した市場レジーム判定（score_regime）
- 研究（Research）用ツール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（品質問題をリスト化）
- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティ（UUID 階層、監査テーブル初期化ユーティリティ）
- 安全性・運用配慮
  - .env 自動ロード（プロジェクトルート基準）、環境ごとの設定、API リトライ / レート制御、Look-ahead バイアス対策

---

## 要件（主な依存）

標準ライブラリ中心ですが、以下が必要／推奨です。

- Python 3.9+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（venv を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージが setuptools 等に設定されていれば:
# pip install -e .
```

---

## 環境変数と設定

config.Settings 経由で環境変数を取得します。自動 .env ロード機能：
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。

主な必須環境変数（Settings で _require を使うもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime にて使用）

その他の設定（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / ...
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PID_FILE_PATH: data/execution.pid
- CPU/MEMORY/DISK 閾値: CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

例：`.env`
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
```

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト
2. 仮想環境を作る（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # お好みで他の必要パッケージを追加
   ```
4. .env を作成（上記参照）
5. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
6. （必要なら）パッケージをローカルインストール
   ```
   pip install -e .
   ```

---

## 使い方（主要 API・ユースケース）

以下はライブラリをプログラムから使う簡単な例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を引数に取ることが多いです。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア算出（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None: OPENAI_API_KEY を使う
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査テーブルを作成）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # :memory: も指定可
# 以降 conn を使って監査テーブルへアクセス
```

- ファクター計算（Research）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

- カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
print(is_trading_day(conn, date(2026, 3, 20)))
print(next_trading_day(conn, date(2026, 3, 20)))
```

注意点:
- 多くの関数は「ルックアヘッドバイアス防止」のため内部で date.today() を使用しない設計になっています。テストやバッチ実行時は target_date を明示的に渡してください。
- OpenAI 呼び出しはリトライ・フォールバックが実装されていますが、API キーは環境に設定してください。

---

## 推奨運用フロー（簡易）

1. 毎朝（夜間バッチ）に run_daily_etl を実行してデータを最新化
2. raw_news を収集して score_news で銘柄センチメント登録
3. score_regime で市場レジーム更新（ポートフォリオ配分などの上流へ）
4. strategy 層でファクター・シグナル生成 → order_requests に記録して執行

監視・通知は Slack 等を用いて設定してください（SLACK_* 環境変数）。

---

## 主要モジュールの役割（簡単な説明）

- kabusys.config: 環境変数 / .env 読み込みと Settings クラス
- kabusys.data.jquants_client: J-Quants API の取得・保存ロジック（ページネーション／レート制御／リトライ）
- kabusys.data.pipeline: ETL のエントリポイントと個別 ETL ジョブ（run_daily_etl 等）
- kabusys.data.news_collector: RSS フィード収集、前処理、raw_news への保存（SSRF 対策等）
- kabusys.data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.calendar_management: 市場カレンダー管理（営業日判定、next/prev）
- kabusys.data.audit: 監査ログテーブルの DDL と初期化ユーティリティ
- kabusys.ai.news_nlp: ニュースを LLM に渡して銘柄センチメントを算出（score_news）
- kabusys.ai.regime_detector: ETF + マクロニュースで市場レジーム判定（score_regime）
- kabusys.research: ファクター計算・特徴量調査ユーティリティ

---

## ディレクトリ構成（抜粋）

以下は主要ファイル/ディレクトリの構成イメージ（src/kabusys 以下）。

- src/kabusys/
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
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: schema 初期化等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/ (上記)
  - research/ (上記)

（リポジトリにはさらに strategy / execution / monitoring 等のパッケージも想定されていますが、上記はこのコードベースで提供されている主要コンポーネントです。）

---

## 補足・注意事項

- この README はコードベースに記載された設計方針・関数シグネチャ等に基づき作成しています。実際の運用では DB スキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar, news_symbols 等）が必要になります。スキーマ初期化用の関数や SQL が別途あることを想定してください。
- OpenAI / J-Quants API を呼ぶ箇所は実キーが必要です。テスト時は該当関数（内部の _call_openai_api 等）をモックする設計になっています。
- .env の自動読み込みはプロジェクトルートの検出に依存します。意図しない読み込みを防ぐ場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

必要があれば README に以下を追加できます：
- サンプル .env.example（各キーの説明）
- DuckDB のスキーマ定義 SQL（テーブル定義）
- CI / テスト実行方法
- 具体的な運用 cron / systemd の例

要望があれば追記します。