# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム向けユーティリティ群を集めた Python パッケージです。データ ETL、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注・約定トレーサビリティ）など、戦略開発および運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務情報、JPX カレンダーを差分取得して DuckDB に保存するパイプライン（冪等処理、トークン自動リフレッシュ、レート制御、リトライ実装）。
- ニュース収集 / NLP
  - RSS からニュースを収集し前処理して raw_news に保存。OpenAI（GPT 系）を用い銘柄ごとのニュースセンチメント（ai_scores）を算出。
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次でレジーム判定（bull/neutral/bear）。
- 研究（Research）機能
  - モメンタム / ボラティリティ / バリュー等のファクター算出、将来リターン・IC・統計サマリ等のユーティリティ。
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue レポート。
- 監査ログ（Audit）
  - signal → order_request → execution までのトレーサビリティ用テーブルを DuckDB 上に初期化・管理。
- 設定管理
  - .env や環境変数から自動で設定読み込み（プロジェクトルート検出、.env.local による上書き、無効化フラグあり）。

---

## 必要環境・依存関係

- Python 3.10 以上（型注釈で新しい構文を利用）
- 必要パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで動く箇所も多いですが、AI 関連や DuckDB を使うには上記が必要です。

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを開発モードでインストールする場合
pip install -e .
```

（プロジェクトに requirements.txt や pyproject.toml があればそちらを利用してください）

---

## 必要な環境変数（主要）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードはデフォルト有効。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（コード内で _require() によってチェックされるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT などの監視設定
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

AI 関連（OpenAI）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）

.env のパースは一般的な shell 形式に対応し、`.env.local` が `.env` を上書きします。OS 環境変数が最優先です。

---

## セットアップ手順（ローカル向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトの依存定義があればそれを使う
   # pip install -r requirements.txt
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くか、OS 環境変数として設定します。
   - 最低限 JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（AI を使う場合）、および KABU_API_PASSWORD / SLACK_* が必要です。

5. データベースを用意
   - デフォルトでは `data/kabusys.duckdb` が使われます（settings.duckdb_path）。
   - 監査用 DB を初期化する場合は下の Usage を参照してください。

---

## 使い方（サンプル）

以下は主要なエントリポイントの簡単な利用例です。実際には適切なロギング設定やエラーハンドリングを行ってください。

- DuckDB 接続を開いて日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.duckdb")
# 以降 conn を使って監査ログ操作が可能
```

- ETL 結果のチェックや品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意:
- score_news / score_regime は OpenAI API を使用します。api_key を引数で渡すことも可能（省略時は環境変数 OPENAI_API_KEY を参照）。
- 各関数はルックアヘッドバイアスを避ける設計になっており、target_date を明示的に渡すことを前提としています。

---

## 自動環境読み込みの挙動

- パッケージ import 時に自動でプロジェクトルートを探索（__file__ の親を上に辿り .git または pyproject.toml を探す）し、見つかった場合は `.env` → `.env.local` の順で読み込みを行います。
- OS 環境変数が既に設定されているキーは上書きされません（`.env.local` は override=True で上書きしますが、OS 環境変数は保護されます）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主なディレクトリ/ファイル構成（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（LLM を使った銘柄センチメント）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl など）
    - jquants_client.py       — J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py       — RSS ニュース収集（SSRF 対策・前処理）
    - calendar_management.py  — 市場カレンダー管理（営業日判定・更新ジョブ）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログテーブル定義 / 初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ 等

---

## 設計上のポイント（抜粋）

- ルックアヘッドバイアス対策: 多くの関数は date 今日参照を避け、明示的な target_date 引数を使う設計。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE などで冪等に実装。
- フェイルセーフ: 外部 API の失敗時は一部処理をスキップして継続する設計（例: LLM 呼び出し失敗時にゼロスコアで続行）。
- セキュリティ: RSS 収集では SSRF 対策、XML パースは defusedxml を利用。J-Quants 呼び出しはレート制御とリトライ実装あり。
- テスト容易性: OpenAI 呼び出しや HTTP 層は差し替え可能（モック化を想定して private 関数を切り出し）。

---

## 開発 / 貢献

- コードのスタイルやテストについてはリポジトリ内の CONTRIBUTING.md（存在する場合）を参照してください。
- 主要な外部サービス（J-Quants / OpenAI / Slack / kabuAPI）への接続情報は環境変数で管理します。実動作を行う前に sandbox / paper_trading 環境で十分に検証してください。

---

もし README に追加したい具体的なインストール手順（pyproject.toml / requirements.txt に基づく）、CI 設定、あるいはより詳しい使用例（フル ETL スケジュールや Slack 通知例）があれば教えてください。README を拡張して反映します。