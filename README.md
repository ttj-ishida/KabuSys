# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント分析）、ファクター計算、監査ログ（トレーサビリティ）、カレンダー管理などを提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ取得・ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（差分 / ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合検出（quality モジュール）
- カレンダー管理
  - 営業日判定 / 翌営業日・前営業日の探索 / 期間内営業日取得
  - 夜間のカレンダー更新ジョブ（calendar_update_job）
- ニュース収集
  - RSS から記事を取得・前処理し raw_news に格納（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM で評価して ai_scores に保存（score_news）
  - マクロニュースと ETF（1321）のMA乖離を合成して市場レジーム判定（score_regime）
- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル生成・初期化（DuckDB）
  - 監査用 DB 初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - .env / .env.local / OS 環境変数から自動ロード（config モジュール）
  - 必須環境変数チェック（settings オブジェクト）

---

## 必要要件

- Python 3.10+
- パッケージ依存（代表例）
  - duckdb
  - openai
  - defusedxml
（プロジェクトの配布方法により requirements.txt / pyproject.toml があるはずです。なければ上記を pip install してください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
pip install -e .
```

---

## 環境変数

自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須変数:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL 認証）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視通知等）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で未指定時に参照）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）

簡単な .env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール
   （プロジェクトに requirements.txt / pyproject があればそちらを使ってください）
   ```
   pip install duckdb openai defusedxml
   pip install -e .
   ```

4. 環境変数を設定（.env を作成）
   - 先述の例を参照して `.env` を用意してください。
   - 開発時は `.env.local` でローカル上書きが可能です。

---

## 使い方（主要 API と実行例）

以下はライブラリの一部関数を使うためのサンプルコードです。実行前に必要な環境変数が設定され、DuckDB のスキーマ（必要テーブル）が存在することを想定します。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 今日分の ETL を実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを環境変数 OPENAI_API_KEY に設定済みであること
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー更新ジョブ
```python
from datetime import date
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存レコード数: {saved}")
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセス可能
```

- リサーチ用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

ログレベルや動作環境の違いは settings（kabusys.config.settings）で参照できます。

---

## 注意点 / 設計ポリシー（抜粋）

- ルックアヘッドバイアス対策
  - 多くの処理（ニュースウィンドウ、MA計算、ETL の target_dateなど）は内部で datetime.today() を用いず、明示的に target_date を受け取る設計です。バックテスト時に未来情報を参照しない設計になっています。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）の失敗は多くの箇所でフォールバック（0.0 を返す等）して処理継続を試みます。ただし、重要な必須変数がない場合は ValueError を投げます。
- 冪等性
  - DuckDB への保存は可能な限り ON CONFLICT（UPSERT）で冪等に行います。
- セキュリティ
  - RSS 収集は SSRF 対策、XML インジェクション対策、受信サイズ制限を実装しています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                         - 環境変数 / 設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                      - ニュースセンチメント / score_news
  - regime_detector.py               - マクロ + MA 合成の市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                - J-Quants API クライアント（fetch / save）
  - pipeline.py                      - ETL パイプライン（run_daily_etl 等）
  - etl.py                           - ETLResult の再エクスポート
  - calendar_management.py           - 市場カレンダー管理
  - stats.py                         - 統計ユーティリティ（zscore_normalize）
  - quality.py                       - データ品質チェック
  - news_collector.py                - RSS ニュース収集
  - audit.py                         - 監査ログ（テーブル定義 / 初期化）
- research/
  - __init__.py
  - factor_research.py               - モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py           - 将来リターン / IC / 統計サマリー

（上記は主要ファイルの抜粋です。実際のリポジトリではさらに strategy / execution / monitoring 等のモジュールが存在します。）

---

## 開発 / テスト

- 環境変数の自動ロードは .env/.env.local をプロジェクトルートから検出します。ユニットテストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- OpenAI 呼び出し部分は内部で独立したラッパー関数を使っているため、unittest.mock.patch で差し替え容易（テストしやすい設計）。

---

## ライセンス / 貢献

ライセンス情報や貢献ガイドは本リポジトリのトップレベル（LICENSE / CONTRIBUTING.md）を参照してください。

---

不明点や README に追加したい内容（例: 実行スクリプト、CI 設定、より詳しいテーブルスキーマなど）があれば教えてください。必要に応じてサンプルの .env.example や起動スクリプトを作成します。