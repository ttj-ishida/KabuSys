# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレース）などの機能を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フォールトトレラント（APIエラー時のフェイルセーフ）」です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件（Dependencies）
- セットアップ手順
- 環境変数（.env）
- 使い方（簡単なコード例）
- ディレクトリ構成（主なファイルと説明）
- よくある注意点

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から日本株の株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- 保存データに対する品質チェック（欠損、スパイク、重複、日付不整合）
- RSS ベースのニュース収集と記事の前処理（SSRF対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（銘柄ごと・マクロ判定）
- 市場レジーム判定（ETFのMA乖離 + マクロニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- 監査ログ（signal → order_request → execution をトレースする監査テーブル）初期化ユーティリティ

---

## 機能一覧

- 環境設定管理（auto .env ロード、必要変数チェック）: `kabusys.config`
- J-Quants API クライアント（レート制御・自動トークンリフレッシュ・リトライ）: `kabusys.data.jquants_client`
- ETL パイプライン（prices / financials / calendar の差分更新）: `kabusys.data.pipeline`, `run_daily_etl`
- データ品質チェック（欠損・スパイク・重複・日付不整合）: `kabusys.data.quality`
- ニュース収集（RSS、SSRF防御、トラッキング除去）: `kabusys.data.news_collector`
- AI スコアリング
  - 銘柄ニュースのセンチメント（バッチ）: `kabusys.ai.news_nlp.score_news`
  - マクロニュース + ETF MA200 を使った市場レジーム判定: `kabusys.ai.regime_detector.score_regime`
- 研究ユーティリティ（モメンタム・バリュー・ボラティリティ等）: `kabusys.research.*`
- 共通統計ユーティリティ（Zスコア正規化など）: `kabusys.data.stats.zscore_normalize`
- 監査ログスキーマ初期化（DuckDB 用）: `kabusys.data.audit.init_audit_db` / `init_audit_schema`

---

## 前提条件（Dependencies）

最低限必要なパッケージ（代表例）:

- Python 3.10+
- duckdb
- openai
- defusedxml

例:
```bash
pip install duckdb openai defusedxml
```

備考:
- その他、プロジェクト固有の依存（HTTPクライアント等）がある場合は pyproject.toml / requirements.txt を利用してください。
- OpenAI SDKのバージョンにより例外クラス名が異なるため、ある程度の互換性を想定した実装になっています。

---

## セットアップ手順

1. リポジトリをクローン:
   ```bash
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール:
   - 最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発時は他のツール（lint, test）を追加してください。

4. パッケージを editable インストール（任意）:
   ```bash
   pip install -e .
   ```

5. 環境変数設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みはデフォルトで有効）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数です（必須は注記）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等（本実装では設定保持）
- KABU_API_BASE_URL — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視等で使用）
- PID_FILE_PATH — 実行監視用 PID ファイルパス
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で利用）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（簡単なコード例）

以下は DuckDB に接続して各処理を呼ぶ最小例です。実際はエラーハンドリングやログ設定を行ってください。

- ETL（日次 ETL 実行）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（OpenAI を用いる）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査DB の初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降、conn を使って監査テーブルへ書き込む/参照する
```

---

## ディレクトリ構成（主要ファイルと説明）

以下はパッケージ内の主要モジュールと役割の概観（一部抜粋）:

- src/kabusys/__init__.py
  - パッケージのエントリ。バージョン情報など。

- src/kabusys/config.py
  - 環境変数の自動読み込み (.env / .env.local)、必須変数チェック、Settings クラス。

- src/kabusys/ai/
  - news_nlp.py: ニュース記事の銘柄ごとセンチメント評価（OpenAI 呼び出し・バッチ処理・レスポンス検証）
  - regime_detector.py: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（認証、取得、保存関数、レート制御、リトライ）
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - etl.py: ETLResult の再公開インターフェース
  - news_collector.py: RSS からニュース収集、前処理、raw_news への保存ロジック（SSRF対策含む）
  - calendar_management.py: market_calendar の管理と営業日判定ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: 共通統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログ（signal / order_requests / executions）テーブル定義・初期化

- src/kabusys/research/
  - factor_research.py: ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - feature_exploration.py: 将来リターン計算、IC（Spearman）計算、統計サマリーなど
  - __init__.py: 研究用ユーティリティの公開

- src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py, src/kabusys/data/__init__.py
  - 各サブパッケージの公開 API（必要なものをまとめてエクスポート）

---

## よくある注意点 / トラブルシューティング

- 環境変数が未設定だと Settings のプロパティで ValueError が発生します。必須変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_* など）を設定してください。
- OpenAI 呼び出しは API エラー・レート制限に対してリトライ実装がありますが、課金やレートに注意してください。
- DuckDB へ大量 INSERT を行うため、ファイルパスの権限やディスク容量に注意してください。
- news_collector は RSS のリダイレクト等で SSRF を警戒しており、プライベートアドレスや非 http/https スキームを拒否します。動作確認用には公開 RSS を使ってください。
- テストや CI で自動 .env ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- パッケージ内で datetime.today() / date.today() を直接参照しない実装方針になっています（ルックアヘッドバイアス防止）。テストで任意の日付を与えて実行してください。

---

この README はコードベースの主要機能をまとめた概要です。詳細な使用方法、SQLスキーマ定義、運用フロー（ETL スケジュール、監視、Slack 通知など）はプロジェクトの設計ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README に追加すべき運用手順や具体的な設定例（.env.example）を作成します。