# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログなど、戦略開発・バックテスト・本番運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得・保存（J-Quants API 経由）
  - daily quotes（OHLCV）、財務データ、JPX カレンダーの差分フェッチと冪等保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - run_daily_etl による市場カレンダー / 株価 / 財務の一括差分更新
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP（OpenAI）
  - RSS 取得、安全対策（SSRF/サイズ上限/トラッキング除去）
  - gpt-4o-mini を用いた銘柄ごとのニュースセンチメント解析（ai_scores に保存）
  - マクロニュースとETF（1321）MA200乖離から市場レジーム判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
- 汎用ユーティリティ
  - 日付/カレンダー管理（営業日判定, next/prev trading day 等）
  - 統計ユーティリティ（Zスコア正規化 等）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## 環境変数

config.Settings により環境変数から設定を読み込みます。自動でプロジェクトルートの `.env` → `.env.local` を読み込み（OS 環境変数優先）します。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの pyproject.toml / requirements.txt があればそれを利用
   pip install -e .
   ```

4. 環境変数を設定（`.env` をプロジェクトルートに作成）
   - 上記「環境変数」セクションを参照

5. DuckDB データベースファイルの準備（必要に応じて）
   - デフォルトは `data/kabusys.duckdb`（settings.duckdb_path）

---

## 使い方（主なユースケース）

以下はシンプルな Python スニペット例です。実行前に必要な環境変数が設定されていることを確認してください。

- ETL（日次更新）の実行例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄ごと）をスコアリング
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化（監査専用 DB を作成して接続を取得）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- カレンダー / 営業日ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 研究用: ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
momentum = calc_momentum(conn, target)
value = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

---

## 自動 .env 読み込みについて

パッケージ起動時に、プロジェクトのルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` → `.env.local` の順で自動読み込みします。OS 環境変数が優先されます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

読み込みルールのポイント:
- `.env.local` は `.env` より優先（上書き）
- OS 環境変数は上書きされない（保護）
- export プレフィックスやシングル/ダブルクォート、コメントに対応するパーサ実装済み

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py             — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py         — ニュース NLP（OpenAI 経由で銘柄スコア）
      - regime_detector.py  — マクロ + ETF で市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py   — J-Quants API クライアント + DuckDB 保存
      - pipeline.py         — ETL パイプライン / run_daily_etl 等
      - etl.py              — ETL インターフェース公開
      - news_collector.py   — RSS 取得・前処理・保存
      - calendar_management.py — 市場カレンダー管理 / 営業日判定
      - quality.py          — データ品質チェック
      - stats.py            — 統計ユーティリティ（zscore_normalize）
      - audit.py            — 監査ログテーブル定義・初期化
    - research/
      - __init__.py
      - factor_research.py  — ファクター計算（momentum/value/volatility）
      - feature_exploration.py — 将来リターン / IC / summary / rank
    - research/（その他モジュール）
    - （その他）strategy / execution / monitoring 等の名前空間は __all__ に定義されているが、上記が主要実装

（上記はリポジトリの現行実装に基づく抜粋です）

---

## 設計上の注意点 / ガイドライン

- ルックアヘッドバイアス防止
  - モジュール内の多くの関数は date / target_date を明示的に受け取り、内部で `date.today()` や `datetime.today()` を参照しない設計です。バックテスト用途では必ず過去データのみを参照するようにしてください。
- 冪等性
  - J-Quants 保存関数や ETL は ON CONFLICT DO UPDATE を利用して冪等性を確保しています。
- フェイルセーフ
  - OpenAI や外部 API の失敗は基本的に例外を炸裂させずフェイルセーフ（0 やスキップ）で続行する設計の箇所があります。ログで失敗を確認してください。
- テスト容易性
  - 外部呼び出し点（OpenAI API 呼び出し、HTTP open 等）は差し替え可能（モック）なように実装されています。

---

## 貢献 / 開発

- コードスタイル、型注釈（Python 3.10 の構文）を活用しています。
- 外部 API を叩く箇所は安全性（レート制限・リトライ・SSRF 対策）を重視しています。
- 変更や拡張を行う際は、ETL の冪等性とテスト可能性に注意して実装してください。

---

## ライセンス / 注意事項

- 本リポジトリには外部 API キー（J-Quants / OpenAI / Slack 等）が必要です。機密情報はリポジトリに含めないでください。
- 実際の売買を行う場合は十分な検証とリスク管理を行ってください（例: paper_trading 環境での検証）。

---

必要であれば README に以下を追加します:
- 部分ごとの API ドキュメント（関数シグネチャの詳細）
- さらに詳しいセットアップ（Docker / CI / systemd ジョブ例）
- 開発用のテスト・モック手順

どれを優先して追加しますか？