# KabuSys

日本株向けの自動売買・データ基盤ライブラリセットです。  
ETL（J-Quants からの市場データ取得・保存）、ニュース収集・NLP（OpenAI を利用した記事センチメント解析）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを含みます。

主な設計方針は「ルックアヘッドバイアス排除」「冪等性」「フォールトトレランス（API失敗時のフェイルセーフ）」「DuckDB を用いた軽量データレイヤー」です。

---

## 主な機能

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPXカレンダーを差分取得して DuckDB に保存（冪等保存）
  - ETL パイプライン（run_daily_etl）と個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集 / 前処理
  - RSS フィード収集（SSRF 対策・gzip/サイズ制限・URL 正規化・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - JSON Mode（gpt-4o-mini 等）を用いた安定的な構成・リトライロジック

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）算出、ファクター統計サマリ
  - Zスコア正規化ユーティリティ

- 監査（Audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
  - 発注から約定までの UUID ベースでのトレーサビリティ

- 共通ユーティリティ
  - 環境設定管理（kabusys.config: .env 自動読み込み、必須設定の検証）
  - DuckDB 用ユーティリティ、J-Quants クライアント（レートリミット・リトライ・トークン自動更新）

---

## 必要要件

- Python 3.10+
- 推奨パッケージ（実行に必要な主なライブラリ）:
  - duckdb
  - openai
  - defusedxml

環境によっては追加で標準ライブラリ以外が必要になることがあります（例: SSL、ネットワーク周り）。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発用: pip install -e .（pyproject/setup がある場合）
```

（リポジトリに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

---

## 環境変数（.env）

プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（優先順: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（最低限設定が必要なもの）:
- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD       (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL       (任意) — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY          (必須: AI 機能を使う場合) — OpenAI API キー
- SLACK_BOT_TOKEN         (必須: Slack 通知を使う場合)
- SLACK_CHANNEL_ID        (必須: Slack 通知を使う場合)
- DUCKDB_PATH             (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH             (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV             (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL               (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `from kabusys.config import settings` でアクセスできます。必須の値がないとプロパティアクセス時に ValueError を送出します。

---

## セットアップ手順（概要）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   # 必要に応じて他の依存もインストール
   ```

3. 環境変数を設定（プロジェクトルートに `.env` を作成）
   - .env に上記の必須キーを設定します。

4. ディレクトリ準備
   ```bash
   mkdir -p data
   ```

5. 監査 DB の初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要ユースケース）

以下は簡単な Python スニペット例です。実際の運用ではログ/エラーハンドリングやスケジューラ（cron, Airflow など）を追加してください。

- DuckDB への接続（設定で指定したパスを利用）
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は DuckDB 接続
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で指定
print(f"scored {count} symbols")
```

- 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査テーブル初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- リサーチ関数例
```python
from kabusys.research.factor_research import calc_momentum, calc_value
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
# さらに kabusys.data.stats.zscore_normalize などを組み合わせて解析
```

---

## 自動 .env 読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml の存在）を基に自動で `.env` / `.env.local` を読み込みます。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で便利です）。
- settings のプロパティは、必須キーが未設定の場合に ValueError を送出します。起動時に早期検知するためです。

---

## ディレクトリ構成（抜粋）

（src/kabusys 配下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース記事の集約・OpenAI 呼び出し・ai_scores 書き込み
    - regime_detector.py  — マクロニュース + ETF(1321) MA200 乖離で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得＋DuckDB への保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 他）
    - etl.py              — ETLResult 再エクスポート
    - news_collector.py   — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダーの管理・営業日判定・更新ジョブ
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 計算
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリ

各モジュールは docstring に設計方針・処理フロー・フォールトトレランスの挙動を詳細に記載しています。実装を拡張する際は docstring に従ってください。

---

## ログ / モード

- KABUSYS_ENV により動作モードを切り替えます（development / paper_trading / live）。
- LOG_LEVEL 環境変数でログレベルを指定可能（デフォルト INFO）。

---

## テスト / 開発

- ユニットテストを書く際は、OpenAI 呼び出しや外部ネットワーク呼び出しをモックしてください。コード内にモック差替えポイント（関数単位での patch）を意識した設計があります（例: kabusys.ai.news_nlp._call_openai_api のモックなど）。
- 自動 .env 読み込みを無効にしたいときは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 貢献・拡張のヒント

- 新しい ETL ソースを追加する場合は jquants_client の設計に倣い、「取得関数（fetch_*）→ 整形 → save_*」の流れで追加してください。常に冪等性（ON CONFLICT）を考慮してください。
- OpenAI のプロンプト・モデル変更は ai/news_nlp.py と ai/regime_detector.py に限定して変更してください。両モジュールは失敗時のフェイルセーフ（スコア 0.0 等）を実装済みです。
- 監査テーブルのスキーマ変更は backward compatibility を意識し、DDL は idempotent に保ってください（CREATE IF NOT EXISTS 等）。

---

README はここまでです。必要であれば以下を提供できます：
- .env.example の完全なテンプレート
- 具体的な Docker / systemd / Cron の実行例
- サンプルスクリプト（ETL バッチ・ニュース収集ジョブ・Signal→Order のワークフロー）