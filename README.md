# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（発注トレース）など、投資システムのバックエンド処理を網羅するモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - `.env` / `.env.local` 自動読み込み（OS環境変数優先、上書き挙動制御、無効化フラグあり）
  - 必須設定のラズバリチェック（未設定時に ValueError）

- データ ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策、サイズ上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM（gpt-4o-mini）でセンチメント評価 → ai_scores に保存
  - レート制限・429/ネットワーク/5xx に対するエクスポネンシャルバックオフ

- 市場レジーム判定（AI 合成）
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して
    日次でレジーム（bull / neutral / bear）を market_regime に記録

- リサーチ・ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - forward returns / IC / 統計サマリなどの解析ユーティリティ

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出する品質チェック（QualityIssue オブジェクトで返却）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを定義・初期化
  - UUID によるトレース、発注冪等キーの設計

- 共通ユーティリティ
  - 日付・マーケットカレンダー管理、Zスコア正規化など

---

## 前提・依存関係

- Python 3.10+
- 主な外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml を用意している前提です。開発環境では仮想環境を作成して依存をインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ化されていれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. 環境変数の設定
   - プロジェクトルートに `.env` を置くと、自動的に読み込まれます（.git または pyproject.toml を基準に検出）。
   - 読み込み順序: OS 環境変数 > `.env.local` > `.env`
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに利用）。

必須環境変数（実行する機能に応じて必要になる）:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（ETL）
- OPENAI_API_KEY         — OpenAI API キー（ニュース NLP / レジーム判定）
- KABU_API_PASSWORD     — kabuステーション API パスワード（発注機能がある場合）
- SLACK_BOT_TOKEN       — Slack 通知用ボットトークン（通知を使う場合）
- SLACK_CHANNEL_ID      — Slack チャンネル ID（通知を使う場合）

任意設定:
- KABUSYS_ENV           — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH           — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           — SQLite（monitoring 用）ファイルパス（デフォルト: data/monitoring.db）

サンプル `.env`（プロジェクトルートに置く）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主な API と実行例）

このパッケージはライブラリとして使用します。以下は代表的な利用例です。

1) DuckDB 接続と settings
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日の日付を使用します（内部で営業日に調整）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（AI）で銘柄ごとのスコアを計算して保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {written} scores")
```
- api_key を渡さない場合は環境変数 `OPENAI_API_KEY` を参照します。
- score_news は raw_news と news_symbols を参照し、ai_scores に書き込みます。

4) 市場レジーム判定（株価 + マクロニュースの合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```
- 内部で ETF (1321) の MA が用いられ、news_nlp.calc_news_window に基づく期間のマクロニュースを LLM で評価して合成します。

5) 監査ログ・DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 返される接続は監査ログ用にテーブルとインデックスが作成済み
```

6) ファクター計算 / リサーチ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)

# zscore 正規化
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

7) データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

---

## 自動環境変数読み込みの挙動（補足）

- パッケージ読み込み時に自動でプロジェクトルートを検索し、`.env` と `.env.local` をロードします。
  - 検索基準: このファイル（config.py）から上位ディレクトリを辿り `.git` または `pyproject.toml` を検出した場所をプロジェクトルートとする。
- 読み込み優先度:
  1. OS 環境変数（既にセットされている値は保護される）
  2. `.env.local`（存在すれば OS 変数を上書きするが、上位で保護された OS 変数は上書きされない）
  3. `.env`
- 自動ロードを無効にする:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを行いません（テスト環境での切り替えに便利）。

---

## 主要ディレクトリ構成

リポジトリの主なファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLU / OpenAI 呼び出し、ai_scores 書込み
    - regime_detector.py    — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - calendar_management.py— マーケットカレンダー管理 / 営業日判定
    - news_collector.py     — RSS 収集 / 前処理
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログ（信号 → 発注 → 約定 のスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等
    - feature_exploration.py— forward returns / IC / summary / rank

（上記は主なモジュールを抜粋した構成です）

---

## テスト & モックについて（簡単な注意）

- OpenAI への実際の API 呼び出しや外部 HTTP を伴う処理はテストでモック可能な形に設計されています。各モジュール内に `_call_openai_api` などの関数を分離し、unittest.mock.patch で差し替えられます。
- J-Quants API 呼び出しは get_id_token / _request を経由するため、HTTP 層をモックすることで ETL の単体テストが可能です。

---

## 運用上の注意（重要）

- OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等のシークレットは安全に管理してください（.env は秘密情報をコミットしないでください）。
- 本パッケージはバックテストや実際の発注系と一緒に使うことを想定しています。ライブ発注（is_live）モード時は設定や検証を慎重に行ってください。
- DuckDB に対する executemany の挙動（空リストの禁止など）を考慮した実装になっています。DuckDB バージョン互換性に注意してください。
- LLM 出力パースに失敗した場合はフェイルセーフでスコア 0.0 を採用するなどの設計がなされていますが、運用時にはログ監視を必ず行ってください。

---

## 貢献 / 拡張

- 新しいデータソースの追加（RSS リスト、J-Quants の別エンドポイント）
- 発注実装（kabuステーション連携）や Slack 通知の追加・改善
- LLM のモデル切替やプロンプト改善による精度向上

バグ修正・機能追加の際は、コードの意図（ルックアヘッドバイアス回避、冪等性、フェイルセーフ）を尊重してください。

---

ご不明点や README の追加希望（例: CLI 化、具体的な .env.example のテンプレート、実行スクリプト例）などがあれば教えてください。