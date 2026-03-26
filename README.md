# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータパイプライン、ファクター研究、ニュース NLP（LLM）によるセンチメント評価、
市場レジーム判定、監査ログなどを含む自動売買基盤のライブラリ群です。
主に DuckDB をデータ層として利用し、J‑Quants API / RSS / OpenAI（LLM）を組み合わせて
ETL → 品質チェック → 研究 → シグナル生成 → 発注監査までの基盤を提供します。

---

## 主要な特徴（抜粋）

- データ取得 / ETL
  - J‑Quants API から株価（OHLCV）、財務、マーケットカレンダーを差分取得・冪等保存
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理 & NLP
  - RSS 収集モジュール（SSRF 対策・正規化・冪等保存）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（ai_scores への書き込み）
  - マクロニュースを使った市場レジーム判定（MA200乖離 + LLMセンチメントの合成）
- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターンの計算、IC（Information Coefficient）計算、Zスコア正規化、統計サマリー
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions を含む監査スキーマ（DuckDB）
  - 監査 DB 初期化ユーティリティ
- カレンダー管理
  - JPX マーケットカレンダーの管理・営業日判定・next/prev_trading_day 等のユーティリティ

---

## 必要要件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ：urllib, json, datetime, logging 等）

pip install 用の最低サンプル:
```
pip install duckdb openai defusedxml
```

※パッケージ配布時は requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -e .            # 開発インストール（pyproject.toml / setup がある前提）
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID — Slack のチャンネル ID
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - OPENAI_API_KEY — OpenAI API を使用する場合（score_news / score_regime 等）
   - 任意（デフォルトあり）:
     - KABUSYS_ENV = development | paper_trading | live  （デフォルト: development）
     - LOG_LEVEL = DEBUG|INFO|...（デフォルト: INFO）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（クイックスタート）

以下はライブラリ関数を直接呼ぶ最小例です。実運用ではログ設定や例外処理、スケジューラ等を組み合わせてください。

- DuckDB 接続の取得（例）
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

- ニュースセンチメントスコア（銘柄別）を生成する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込まれた銘柄数を返す
```

- 市場レジームスコアを計算して保存する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに (date, regime_score, regime_label, ma200_ratio, macro_sentiment) を書き込む
```

- 監査ログ用 DB を初期化する（監査専用ファイル）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルと必要なインデックスが作成されます
```

- カレンダー / 営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 設計上の注意（要点）

- Look-ahead bias の防止: 多くの関数は内部で現在日時を直接参照せず、呼び出し側が target_date を明示的に渡す設計です（バックテスト時の過剰適合防止）。
- .env の自動ロード: プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 呼び出し: API エラー時はフェイルセーフとしてゼロスコアやスキップで継続する設計（例: score_news / score_regime は API の失敗を全面的に例外にしない実装箇所あり）。
- DuckDB との互換性: 一部実装は DuckDB の埋め込み制約（executemany の空リスト不可など）に配慮しています。

---

## 主なディレクトリ構成（抜粋）

（プロジェクトルート: src/kabusys/ を想定）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）と API 呼び出しロジック
    - regime_detector.py — マクロ + MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン / run_daily_etl
    - etl.py — ETL 結果型の再エクスポート
    - calendar_management.py — マーケットカレンダー管理・営業日ユーティリティ
    - news_collector.py — RSS 取得・前処理・保存（SSRF 対策等）
    - quality.py — データ品質チェック（欠損/spike/重複/日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ（signal / order / execution）スキーマ + 初期化
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility 等の計算
    - feature_exploration.py — forward returns, IC, factor summary, rank 等
  - (他: strategy/, execution/, monitoring/ モジュールのプレースホルダ等)

---

## よくある質問

- Q: OpenAI の API キーはどの環境変数を使いますか？
  - A: OPENAI_API_KEY（関数呼び出し時に api_key 引数で上書き可能）

- Q: .env の読み込みは自動ですか？
  - A: はい。プロジェクトルートに .env / .env.local を置くと自動で読み込まれます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

- Q: ETL が途中で一部失敗した場合、既存データはどうなりますか？
  - A: 各ステップは個別にエラーハンドリングされ、部分失敗しても他ステップは継続します。ETLResult に errors / quality_issues が格納されます。

---

## 開発・貢献

- コードの安全性（SSRF 対策、XML の defusedxml 使用、外部 API のレート制御とリトライ）、および Look-ahead bias を意識した設計が多く導入されています。
- 機能追加・バグ修正の際は、該当モジュールのユニットテストと DuckDB を使った統合テストの追加をお願いします。

---

この README はリポジトリ内の実装（config, data, ai, research, audit 等）を要約しています。詳細な API ドキュメントや運用手順は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば、運用手順（cron / Airflow / systemd など）向けの実行例も作成しますのでご依頼ください。