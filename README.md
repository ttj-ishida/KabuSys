# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API からのデータ取得、DuckDB を用いた ETL / 品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）など、戦略開発〜運用に必要な共通機能を提供します。

バージョン: 0.1.0  
パッケージ名: `kabusys`

---

## 概要

主な目的は「マーケットデータの取得・品質管理」「ニュースを使った銘柄別 AI スコアリング」「市場レジーム判定」「監査ログを伴う発注トレーサビリティ」を一貫して扱えるようにすることです。  
設計上の特徴：

- DuckDB を主要な永続化エンジンとして利用（軽量・ファイルベース）
- J-Quants API との差分 ETL（ページネーション・レート制御・リトライ）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- Look-ahead バイアス対策（内部処理で datetime.today() を不用意に参照しない）
- フェイルセーフ姿勢：API 失敗時は安全側の既定値にフォールバックし全体処理は継続

---

## 機能一覧

- data:
  - J-Quants クライアント（株価 / 財務 / カレンダーの取得、DuckDB への保存）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - カレンダー（営業日判定・前後営業日の取得）
  - ニュース収集（RSS の安全取得・前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal / order_request / executions テーブル）
  - 統計ユーティリティ（Zスコア正規化など）
- ai:
  - ニュース NLP（銘柄ごとにニュースをまとめて LLM でセンチメントを算出し ai_scores に書き込む）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントの合成）
- research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量解析ツール（将来リターン計算、IC、統計サマリ等）
- config:
  - 環境変数および .env 自動読み込み・設定ラッパー

---

## 必要条件

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動く箇所も多いですが、上記は主要機能で必要）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# ソース開発中なら:
pip install -e .
```

（プロジェクト配布に requirements.txt / pyproject がある想定です。実運用では依存バージョンを固定してください。）

---

## 環境変数 / .env

パッケージの起動時（インポート時）にプロジェクトルート（.git または pyproject.toml）を起点として `.env` / `.env.local` を自動で読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- J-Quants（必須）
  - `JQUANTS_REFRESH_TOKEN` - J-Quants のリフレッシュトークン（ETL で必須）
- OpenAI
  - `OPENAI_API_KEY` - OpenAI API キー（ai.score_news / score_regime で使用）
- kabu ステーション（注文連携がある場合）
  - `KABU_API_PASSWORD` - kabu API のパスワード
  - `KABU_API_BASE_URL` - デフォルト: `http://localhost:18080/kabusapi`
- LINE 通知（任意）
  - `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
- データベースパス（オプション）
  - `DUCKDB_PATH` - デフォルト: `data/kabusys.duckdb`
  - `SQLITE_PATH` - 監視用 sqlite: デフォルト `data/monitoring.db`
- 監視 / PID ファイル
  - `PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`
- システムモード
  - `KABUSYS_ENV` - `development`, `paper_trading`, `live`（デフォルト `development`）
  - `LOG_LEVEL` - `DEBUG|INFO|WARNING|ERROR|CRITICAL`

設定値は `kabusys.config.settings` オブジェクトから読み取れます。例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（ローカル開発 / 実行）

1. リポジトリをクローン
2. 仮想環境を作成してアクティベート
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成し必要な環境変数を設定
   - 最低: `JQUANTS_REFRESH_TOKEN`、`OPENAI_API_KEY`（AI 機能を使う場合）
5. データディレクトリを作成（必要であれば）
```bash
mkdir -p data
```
6. DuckDB ファイルはデフォルト `data/kabusys.duckdb` に保存されます（`settings.duckdb_path` で変更可）。

---

## 使い方（サンプル）

以下は Python スクリプト内での簡単な利用例です。

- DuckDB 接続を作って ETL を実行する（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(__import__("kabusys").config.settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- OpenAI を使ってニュースをスコアリングし ai_scores に保存:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（market_regime テーブルへ保存）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査データベース（監査ログ専用 DuckDB）を初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# これで signal_events / order_requests / executions テーブルが作成されます
```

- J-Quants トークンを手動で取得（内部で自動取得も行います）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を利用
```

注意:
- OpenAI / J-Quants の呼び出しは API キー／トークンが必要です。未設定時は例外が発生します。
- LLM 呼び出しは料金が発生するためテスト時はモック化してください（モジュール内で _call_openai_api が分離されています）。

---

## 運用例（cron / バッチ）

- 日次 ETL を深夜に走らせる（例）:
  - スクリプト `scripts/daily_etl.py` を用意して cron で実行
- ニュース集計・AI スコアリングは ETL 後または営業開始前に実行
- 定期的に `calendar_update_job` を呼んでマーケットカレンダーを更新

---

## 注意事項 / ベストプラクティス

- 本ライブラリは「バックテストの内部ループ」から直接 J-Quants / listed/info を呼ぶことを想定していません。バックテストでは事前に必要なテーブル（stocks 等）を準備してください（Look-ahead バイアス回避のため）。
- OpenAI のレスポンスは常に検証（JSON でのパースとキーの存在）していますが、本番での利用時はリトライ／ログの監視を徹底してください。
- `KABUSYS_ENV` を `live` にする前に、発注 / 約定まわりの実装とリスク管理を十分に検証してください。
- `.env` の自動ロード挙動は便利ですが、CI やテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って明示的に設定を渡すことを推奨します。

---

## ディレクトリ構成（主要ファイル）

以下はソース配下の主要モジュール構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング（ai_scores 書込）
    - regime_detector.py    — 市場レジーム判定（market_regime 書込）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得 / 保存）
    - pipeline.py           — ETL パイプライン（run_daily_etl 他）
    - etl.py                — ETL インターフェース再エクスポート
    - calendar_management.py— マーケットカレンダー管理
    - news_collector.py     — RSS 収集（SSRF 対策・前処理）
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン、IC、統計サマリ
  - ai/, data/, research/ 等はそれぞれのトップ API を提供

---

## サポート / 貢献

- 開発中の機能や仕様の拡張・バグ修正は Pull Request を歓迎します。
- 大量データの処理や本番導入時はログ・監視・例外処理の整備を事前に行ってください。

---

README に記載してほしい追加情報（使用している外部サービスのバージョン、CI のセットアップ、例題スクリプト等）があればお知らせください。必要に応じてサンプルスクリプトや運用手順を追記します。