# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants（株価・財務・カレンダー）、RSSニュース、OpenAI（ニュースNLP）などを組み合わせて、データ取得（ETL）、品質チェック、ファクター計算、ニュースセンチメント、マーケットレジーム判定、監査ログ（トレーサビリティ）を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を安易に参照しない）
- DuckDB を用いたローカルデータレイク志向
- API 呼び出しはリトライ/バックオフ/レート制御を実装
- 冪等性（DB への保存は ON CONFLICT を利用）と監査ログによるトレーサビリティ
- テスト容易性のため外部呼び出しを差し替え可能（モックしやすい実装）

---

## 機能一覧

- データ収集 / ETL
  - J-Quants から株価（daily quotes）、財務データ、JPXマーケットカレンダーを差分取得・保存
  - ETL の結果を ETLResult で取得（品質チェック含む）
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック（quality モジュール）
- ニュース収集・前処理
  - RSS フィード取得（SSRF対策、トラッキングパラメータ除去、XML解析の安全化）
  - raw_news / news_symbols の保存ロジック（冪等）
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini）で評価して ai_scores に保存（news_nlp.score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して市場レジームを daily に判定（regime_detector.score_regime）
- 研究向けユーティリティ
  - ファクター（モメンタム・バリュー・ボラティリティ）計算、将来リターン、IC、統計サマリー等（research パッケージ）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化関数（init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（kabusys.config.settings）

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈に | を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## 環境変数 / .env

kabusys.config.Settings がアプリ設定を提供します。主な環境変数（必須 / 任意）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（実運用時）

OpenAI:
- OPENAI_API_KEY: OpenAI 呼び出しで使用（score_news / score_regime に引数で渡すことも可）

通知（任意）:
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

ファイルパス等（デフォルトあり）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

自動 .env 読み込み:
- パッケージ起点でプロジェクトルート（.git または pyproject.toml）を探索し、優先順位は OS 環境 > .env.local > .env です。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

注意: Settings.jquants_refresh_token や kabu_api_password 等は未設定だと呼び出し時に例外になります。

---

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt  # あれば
   # または個別
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定します。
   - 最低限 .env に以下を入れてください（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - .env.local は .env を上書きする目的で使えます。

4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

下記はライブラリの代表的な使い方例です。実行は仮想環境内で行ってください。

共通: Settings と DuckDB 接続の取得
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date None => 今日
print(result.to_dict())
```

2) ニュースセンチメントを算出して ai_scores テーブルに書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
print("ai_scores written:", n_written)
```

3) 市場レジームを判定して market_regime に保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# テーブルが作成され、UTC タイムゾーンが設定されます
```

5) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意点:
- OpenAI API 呼び出しを行う関数は api_key 引数でキー注入可能（テスト時に None を避ける）
- ネットワーク系の関数は自動リトライやフェイルセーフ（失敗時 0.0 / 空辞書等）を行う設計ですが、API キー未設定だと ValueError を投げます
- テスト時はモジュール内の _call_openai_api や network ハンドラをモックして外部呼び出しを置き換えられます（コード中にモック推奨箇所のコメントあり）

---

## 開発 / テストに関するヒント

- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストで環境汚染を避ける場面で有用）。
- OpenAI 呼び出しは news_nlp._call_openai_api / regime_detector._call_openai_api を unittest.mock.patch で差し替えてテスト可能です。
- J-Quants クライアントは内部でレート制御とリトライを行います。大量取得時は rate limit に注意してください（120 req/min）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ宣言・バージョン
  - config.py — 環境変数と Settings 管理、.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）処理・OpenAI 呼び出し・結果の保存
    - regime_detector.py — 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — マーケットカレンダー管理（営業日判定など）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック群（check_missing_data, check_spike, ...）
    - audit.py — 監査ログ（監査テーブル DDL と初期化 helper）
    - news_collector.py — RSS ニュース収集・前処理・保存ロジック
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等

各モジュールは README 内の「機能一覧」に対応する責務を持ち、DuckDB 接続（duckdb.DuckDBPyConnection）を受け取って操作する設計です。

---

## 付記・注意事項

- 実際の売買・発注機能（kabuステーション等）との統合部分は設定やパスワード等の取り扱いに注意してください（テスト環境と本番環境は明確に分けてください）。
- データベースファイルや API トークンは安全に管理してください（.gitignore で data/ や .env を除外する等）。
- 本ライブラリは研究と自動化用のユーティリティを提供しますが、実際の運用では十分なリスク管理・検証を行ってください。

---

必要であれば README に含めるコマンド例や、より詳細な環境変数説明（全プロパティ列挙）、CI/デプロイ手順、テスト例を別途作成します。どの情報を追加しましょうか？