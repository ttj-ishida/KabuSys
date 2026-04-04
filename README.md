# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
J-Quants API や RSS ニュースを取り込み、DuckDB ベースでデータを保持・品質チェックし、LLM を用いたニュースセンチメント・市場レジーム判定、ファクター計算や ETL パイプライン、監査ログ（トレーサビリティ）機能を提供します。

主な目的は「データ取得 → 品質検査 → 特徴量生成 → シグナル/監査 → 発注」といった自動売買プラットフォームの基盤を安全に実装することです。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants から株価（OHLCV）、財務情報、マーケットカレンダーを差分取得（ページネーション・認証・レート制御付き）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- ニュース収集・前処理
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、XML セキュリティ）
  - raw_news / news_symbols テーブルへの冪等保存
- AI（LLM）による解析
  - 銘柄ごとのニュースセンチメントスコア化（gpt-4o-mini を利用）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの組合せ）
  - OpenAI 呼び出しはリトライ・フェイルセーフ設計（API 失敗時はフォールバック）
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - zscore 正規化ユーティリティ
- カレンダー管理
  - market_calendar を元に営業日判定・前後営業日取得
  - JPX カレンダー夜間更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義、初期化ユーティリティ
  - トレーサビリティを UUID 連鎖で保証
- DuckDB による永続化（冪等保存 / ON CONFLICT ロジック）

---

## 必要条件

- Python 3.9+
- 必須ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）
- 環境変数に API キー等を設定する必要あり（下記参照）

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらに従ってください）

---

## インストール（開発環境）

1. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. リポジトリルートでインストール
   - pip install -e ".[dev]" など（もし extras が定義されていれば）
   - 最低限:
     - pip install duckdb openai defusedxml

3. ソース配置は src/kabusys 形式（この README はソースレイアウトに基づきます）。

---

## 環境変数 / 設定

パッケージはプロジェクトルート（.git または pyproject.toml を探索）で `.env` / `.env.local` を自動読み込みします（OS 環境変数を優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須/任意）:
- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。kabusys.data.jquants_client.get_id_token で使用。
- KABU_API_PASSWORD (必須)  
  kabuステーション API パスワード（発注モジュールで使用）。
- OPENAI_API_KEY (必須 for AI)  
  OpenAI API キー（news_nlp / regime_detector のデフォルト）。
- LINE_CHANNEL_ACCESS_TOKEN (任意)  
  LINE 通知用。
- LINE_USER_ID (任意)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
  DuckDB ファイルパス（expanduser 対応）。
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視用設定
- KABUSYS_ENV (任意, development/paper_trading/live デフォルト: development)
- LOG_LEVEL (任意, DEBUG/INFO/... デフォルト: INFO)

設定は kabusys.config.settings 経由で利用できます。

例 .env（最低限の例）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-xxx
  KABU_API_PASSWORD=your_kabu_password
  DUCKDB_PATH=data/kabusys.duckdb

---

## クイックスタート（利用例）

- DuckDB 接続を用意（例: メモリ or ファイル）

Python REPL / スクリプト例:

1) 監査 DB 初期化（監査テーブルを作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント算出
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

※ OpenAI 呼び出しを行う関数（score_news, score_regime）は api_key 引数でキーを上書き可能です。環境変数 OPENAI_API_KEY が未設定の場合は ValueError を送出します。

---

## ディレクトリ構成（主要ファイル）

(src 配下を想定)

- src/kabusys/
  - __init__.py  — パッケージエクスポート
  - config.py    — 環境変数／設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースセンチメント（LLM）実装
    - regime_detector.py — 市場レジーム判定ロジック（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py       — ETL パイプライン（run_daily_etl 等）
    - etl.py            — ETLResult 再エクスポート
    - stats.py          — 統計ユーティリティ（zscore_normalize）
    - quality.py        — データ品質チェック（欠損・スパイク・重複・日付）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py — RSS ニュース収集（SSRF 対策等）
    - audit.py          — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai and research modules rely on DuckDB 接続を受け取る設計（副作用最小化）

---

## 実装上の注意点 / 設計方針

- ルックアヘッドバイアス防止
  - モジュール内部では datetime.today()/date.today() を直接利用せず、target_date を明示的に渡すことでバックテスト時の情報漏洩を防止しています。
- 冪等性
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を用いて冪等保存を実現しています。
- フェイルセーフ
  - LLM の API 失敗やネットワーク障害時は、致命的にはせずフォールバック（例: macro_sentiment=0）して処理を継続する設計箇所があります。
- セキュリティ
  - news_collector では SSRF や XML インジェクション対策（defusedxml、ホスト私的アドレス判定、リダイレクト検査）を実装しています。
- テスト容易性
  - OpenAI 呼び出しや HTTP クライアントは内部関数をモックし差し替え可能な設計です（ユニットテスト向け）。

---

## よくある操作 / トラブルシューティング

- .env が読み込まれない
  - パッケージは .git / pyproject.toml を基準にプロジェクトルートを探索します。プロジェクトルートが見つからない場合は自動読み込みをスキップします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- OpenAI エラーでスコアが返らない
  - LLM 呼び出しはリトライとフォールバック（0.0）を実装しています。APIキーやレート制限を確認してください。
- J-Quants 認証エラー(401)
  - jquants_client は 401 を検出した場合にリフレッシュトークンから id_token を再取得して 1 回リトライします。環境変数 JQUANTS_REFRESH_TOKEN が正しいか確認してください。
- DuckDB ファイルパス
  - デフォルトは data/kabusys.duckdb。settings.duckdb_path で上書き可能。ディレクトリが存在しない場合は自動で作る処理を必要に応じて行ってください（init_audit_db は親ディレクトリ自動作成）。

---

## 開発・寄与

- 各モジュールは DuckDB 接続を明示的に受け取る設計なので、ユニットテストはメモリ DB（":memory:"）やテスト用ファイルで容易に行えます。
- OpenAI / HTTP 呼び出し箇所はモック可能に実装されているため外部依存の切り離しが容易です。

---

この README はソースコードの主要機能と使い方の概要をまとめたものです。詳細な API リファレンスや運用手順、pyproject/requirements の記載はリポジトリの追加ドキュメントを参照してください。