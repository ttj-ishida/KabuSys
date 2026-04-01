# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（LLM 統合）、リサーチ用ファクター計算、監査ログ管理、そして市場レジーム判定などを含みます。

---

## 概要

KabuSys は日本株のデータプラットフォームとリサーチ / 自動売買の基盤機能を提供する Python パッケージです。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足・財務・上場銘柄情報・市場カレンダー）
- DuckDB を用いたローカルデータ格納と冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集・前処理・LLM を使った銘柄単位のニュースセンチメント付与
- 市場レジーム判定（MA と マクロニュースの LLM センチメントの合成）
- リサーチ用ファクター（モメンタム / ボラティリティ / バリュー 等）計算と統計ユーティリティ
- 監査ログ・トレーサビリティ（シグナル → 発注 → 約定 の履歴管理）

---

## 機能一覧

- data
  - jquants_client: J-Quants API 呼び出し、ページネーション、レート制御、DB 保存関数
  - pipeline / etl: 日次 ETL（calendar / prices / financials）、差分・バックフィル、ETLResult
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS からのニュース収集、前処理、SSRF 対策、冪等保存
  - calendar_management: 市場カレンダー管理・営業日判定・更新ジョブ
  - audit: 監査ログ用テーブル定義・初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（z-score 正規化 等）
- ai
  - news_nlp: 銘柄ごとのニュースを LLM（gpt-4o-mini）でスコアリングして ai_scores に書き込む
  - regime_detector: ETF 1321 の MA200 乖離 + マクロニュース LLM で市場レジーム判定・記録
- research
  - factor_research: モメンタム / ボラティリティ / バリュー ファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）、統計サマリー等

---

## 必要条件（主な依存）

- Python 3.9+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- （標準ライブラリ以外の依存は setup で管理してください）

例（pip）:
```bash
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt / setup を使ってインストール
```

---

## 環境変数 / 設定

KabuSys は環境変数を使用して外部 API トークンやパスを参照します。プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector の呼び出しで明示しない場合に参照）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視関連
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO"...)

必須変数が未設定の場合、settings プロパティから参照すると ValueError が発生します。

---

## セットアップ手順（開発用）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -e .           # setup.py / pyproject があれば editable install
   pip install duckdb openai defusedxml
   ```
4. .env を作成（内容例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   ```
5. DuckDB 用ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要 API の例）

以下は最小限の利用例です。どの関数も DuckDB の接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ります。

- DuckDB 接続作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄ごとのスコア付与）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数に渡すか、環境変数 OPENAI_API_KEY を設定する
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じてアプリ DB にマージする、または audit_conn を使って監査ログを操作
```

- リサーチ用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意事項:
- 公開関数の多くは OpenAI API キーや J-Quants トークンを環境変数から自動参照します。テスト時は明示的に api_key / id_token を渡すことが可能です。
- 各関数はルックアヘッドバイアスを避ける設計（target_date を明示）になっています。内部で date.today() を参照しない関数が多いことに注意してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの `src/kabusys` 以下の主要モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (ETLResult 再エクスポート)
  - quality.py
  - stats.py
  - calendar_management.py
  - news_collector.py
  - audit.py
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記は README 作成時点の主要モジュール一覧です。リポジトリ内での細かいファイルは適宜参照してください。）

---

## 実運用・運用上の注意

- API レート制御やリトライは各クライアントで実装していますが、実運用ではさらに監視・アラート（Slack など）を組み合わせることを推奨します。
- OpenAI 呼び出しはコストが発生します。news_nlp / regime_detector は batching / 最大記事数等で制約していますが、API 使用量には注意してください。
- ETL は部分失敗に強い設計（個別ステップで例外をキャッチして継続）になっていますが、品質チェックの結果（result.quality_issues）を適切に扱ってください。
- .env ファイルは秘密情報を含むためバージョン管理に含めないでください。

---

## テスト / 開発補助

- 自動的な .env の読み込みを抑止したいユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワーク I/O 部分はモックしやすい構成（内部関数を patch して差し替え可能）になっています。

---

## 貢献・ライセンス

この README はコードベースの概要説明を目的としたもので、実運用に際しては追加ドキュメント（設計書 / 運用手順 / セキュリティレビュー）を用意してください。  
ライセンス情報・貢献方法はリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください（未設定の場合はプロジェクト方針に従って追加してください）。

---

必要であれば、README にコマンドライン例（cron / systemd 用の記述）、より詳細な設定例、テーブルスキーマの説明（DDL サンプル）等を追記します。どの情報を追加希望か教えてください。