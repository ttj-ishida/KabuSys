# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集と LLM によるニュースセンチメント評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、トレーディングシステム構築に必要なユーティリティをまとめて提供します。

バージョン: 0.1.0

---

## 主な特徴

- 環境変数ベースの設定管理（.env/.env.local の自動ロードをサポート）
- J-Quants API クライアント（株価、財務、JPX カレンダー等の差分取得・保存）
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT / UPDATE）
- ETL パイプライン（run_daily_etl）と結果集約（ETLResult）
- ニュース収集モジュール（RSS 収集、SSRF 対策、前処理、DB 保存）
- ニュース NLP（OpenAI を使った銘柄別センチメント評価: score_news）
  - バッチ処理、JSON モード、堅牢なリトライとバリデーション
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成: score_regime）
- Research ツール群（モメンタム、ボラティリティ、バリュー、将来リターン、IC 等）
- データ品質チェック（欠損、重複、スパイク、日付不整合の検出）
- 監査ログ（signal / order_request / executions）のスキーマ初期化ユーティリティ
- 汎用統計ユーティリティ（Zスコア正規化など）

---

## 要件

- Python 3.10 以上（typing の新しい書式や型ヒントを利用）
- 主要依存ライブラリ（pip 等で導入）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス:
  - J-Quants API への接続（JQUANTS_REFRESH_TOKEN）
  - OpenAI API（AI 関連機能を使う場合）
  - RSS フィード取得（news_collector を使う場合）
- （発注/実行周り）kabuステーション API（KABU_API_BASE_URL / KABU_API_PASSWORD）

必要パッケージはプロジェクトの requirements.txt / pyproject.toml に従ってインストールしてください（本 README はサンプル記述のみ）。

---

## インストール（開発環境向け）

リポジトリをクローンしてパッケージをインストールする例:

```bash
git clone <repo-url>
cd <repo-root>
# 仮想環境を作る（推奨）
python -m venv .venv
source .venv/bin/activate

# 必要依存をインストール（例）
pip install duckdb openai defusedxml

# 開発モードでインストール（setup / pyproject がある場合）
pip install -e .
```

---

## 環境変数（主なもの）

プロジェクトルートにある `.env`/.env.local を自動的に読み込みます（優先: OS env > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack 送信先 channel id

推奨 / 省略時デフォルトあり:
- KABUSYS_ENV            : "development" / "paper_trading" / "live"（default: development）
- LOG_LEVEL              : "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（default: INFO）
- KABU_API_BASE_URL      : kabu API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（モニタリング用）パス（default: data/monitoring.db）
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime など AI を使う機能で参照）

.env の書式はシェルの export/KEY=VALUE 形式に対応し、コメントやクォートも正しく処理されます。

---

## セットアップ手順（簡易ガイド）

1. リポジトリをチェックアウト
2. 仮想環境を作成し依存ライブラリをインストール
3. プロジェクトルートに `.env` を作成（.env.example を参照）
   - 必須トークン類を設定する
4. DuckDB ファイル保存先のディレクトリを作成（自動的に作られることが多い）
5. 必要に応じ `init_audit_db` を実行して監査 DB スキーマを初期化

例: .env の最低例（本番では安全に管理してください）

```
JQUANTS_REFRESH_TOKEN=... 
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主要ユースケース）

以下は Python REPL / スクリプトでの利用例です。各関数は DuckDB 接続（duckdb.connect(...)）を受け取る設計です。

- DuckDB に接続して日次 ETL を実行する:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（ai.news_nlp.score_news）を実行する:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定していること
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）を実行する:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する（専用 DB を使う場合）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルに読み書き可能
```

- Research（ファクター計算、forward returns、IC）例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
forward = calc_forward_returns(conn, date(2026,3,20))
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- カレンダー関連ユーティリティ:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意:
- AI 関連関数は OpenAI API キーを必要とします（引数で注入可能）。
- ETL / 保存処理は冪等性を考慮していますが、実行前にバックアップや確認を行ってください。

---

## 自動 .env ロードの挙動

- 実行開始時にパッケージ内でプロジェクトルートを探索し、`.env` → `.env.local` の順で読み込みます（OS 環境変数は上書きされません）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- プロジェクトルートの判定は `.git` または `pyproject.toml` を基準とします。配布後やルートが見つからない場合は自動ロードをスキップします。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch / save）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETL インターフェース再エクスポート
    - calendar_management.py# マーケットカレンダー管理
    - news_collector.py     # RSS ニュース収集
    - quality.py            # データ品質チェック
    - stats.py              # 統計ユーティリティ（zscore_normalize）
    - audit.py              # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    # Momentum / Value / Volatility 等
    - feature_exploration.py# forward returns, IC, factor summary, rank
  - ai/, data/, research/ のテストや補助モジュールが含まれる場合あり

---

## 開発・貢献

- コードの整合性とルックアヘッドバイアス防止が重要な設計指針になっています。外部 API 呼び出しや日時操作では注意して実装してください。
- テスト時は API コール部分（OpenAI / J-Quants / RSS）をモックする想定です（コード内に patch 用の設計あり）。
- PR の際はユニットテストと簡単なローカル ETL 実行で動作確認してください。

---

## 補足・注意事項

- 本ライブラリは実運用の取引・発注機能を含む場合、十分な検証と慎重な運用が必要です（誤発注のリスク、API レート制限、シークレット管理等）。
- AI 関連は外部サービスに依存するため、API の障害やレスポンスの不確定性に対するフェイルセーフ設計（スコア 0.0 でのフォールバック等）が組み込まれていますが、運用時のモニタリングが重要です。
- J-Quants / OpenAI / kabuステーション の利用規約・課金に注意してください。

---

質問やドキュメントの追記、具体的な使い方サンプルが必要であれば用途に合わせて追加します。