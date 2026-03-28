# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用した銘柄センチメント）、ファクター計算、マーケットカレンダー、監査ログ（発注・約定トレーサビリティ）など、運用・研究フェーズで必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要機能

- 環境設定管理
  - `.env` / 環境変数自動ロード（プロジェクトルート検出）
  - 必須項目チェック（settings オブジェクト）

- データ収集（J-Quants クライアント）
  - 株価日足（OHLCV）の差分取得（ページネーション対応）
  - 財務データ（四半期）取得
  - JPX マーケットカレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）

- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル・品質チェックの実行と結果集約（ETLResult）

- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、重複チェック、将来日付／非営業日チェック
  - 問題を QualityIssue として一覧返却

- ニュース収集
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
  - raw_news / news_symbols への冪等保存を前提に設計

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを LLM に投げてセンチメント（ai_scores）を算出・保存
  - チャンク処理、スコア検証、リトライ実装

- 市場レジーム判定（AI + テクニカル合成）
  - ETF(1321) の 200 日移動平均乖離とマクロニュース LLM スコアを合成して日次レジーム判定

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化
  - 監査用 DuckDB 初期化ユーティリティ（init_audit_db、init_audit_schema）

---

## 動作要件（想定）

- Python 3.10+
- 主な依存パッケージ:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで多くを実装しているため、他は最小限です。

必要に応じて pyproject.toml / requirements.txt を用意してインストールしてください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   例:
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトがパッケージ化されている場合
   pip install -e .
   ```

4. 環境変数を設定（.env に記載してプロジェクトルートに置くことが可能）
   - 自動ロードはパッケージの config モジュールで行われます（.git または pyproject.toml を基準にプロジェクトルートを探索）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（基本例）

以下は Python REPL / スクリプトからの利用例です。

- 設定取得
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_dev)
```

- DuckDB 接続準備（監査DB初期化例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへ書き込みが可能
```

- 日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（特定日）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY を参照
print(f"scored {n_written} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
conn = duckdb.connect(str(settings.duckdb_path))
factors = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "ma200_dev"])
```

注意:
- OpenAI の呼び出しは API キー（OPENAI_API_KEY）を環境変数または関数引数で渡す必要があります。
- J-Quants の呼び出しは `JQUANTS_REFRESH_TOKEN` を設定してください（get_id_token が自動で refresh→id token を取得します）。

---

## 環境変数一覧（重要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時に必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV — 実行環境: development, paper_trading, live
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定取得は `from kabusys.config import settings` を使ってプロパティから行ってください。必須項目は未設定時に ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - pipeline.py            — ETL パイプライン / run_daily_etl 等
    - jquants_client.py      — J-Quants API クライアント + 保存関数
    - news_collector.py      — RSS ニュース収集（SSRF 対策等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（Z-score 等）
    - etl.py                 — ETLResult 再エクスポート
    - audit.py               — 監査ログ（signal / order / executions）初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン・IC計算・サマリー等
  - ai/、data/、research/ はそれぞれ独立したサブパッケージ群です。

---

## 運用上の注意・設計上のポイント

- Look-ahead バイアス対策が意図的に組み込まれています（target_date 未満のデータのみ使用、datetime.today() を直接参照しない等）。
- J-Quants のレート制限（120 req/min）をモジュールレベルで制御します。
- OpenAI 呼び出しはリトライ・JSON 検証・フォールバック（0.0）を行い、API エラーで処理全体が停止しないよう設計されています。
- DuckDB での一括保存は冪等性（ON CONFLICT）を前提にしています。
- ニュース収集は SSRF、XML 攻撃、gzip bomb 等への対策を実装しています（defusedxml、ホスト検査、サイズ制限等）。

---

## サポート / 貢献

バグ報告や機能提案は Issue にて受け付けてください。貢献の際はコード規約（PEP8）に沿い、ユニットテストと簡潔な説明を添えてください。

---

README の内容はコードベースの説明を目的とした概略です。詳細な API や運用手順については各モジュールの docstring を参照してください。