# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）など、取引システムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理（自動 .env ロード、必須キー検証）
- J-Quants API クライアント
  - 株価日足（OHLCV）
  - 財務データ
  - JPX マーケットカレンダー
  - ページネーション・レート制御・リトライ・トークンリフレッシュ対応
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース収集（RSS）と前処理（SSRF対策、トラッキング除去）
- ニュースNLP（OpenAI）による銘柄別センチメントスコアリング（ai_scores への書き込み）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントを合成）
- 研究（research）モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - Zスコア正規化ユーティリティ
- 監査（audit）テーブル群の初期化・管理（signal_events / order_requests / executions）
- DuckDB を用いたオンプレ/ローカルデータベース運用

---

## 前提条件

- Python 3.10+
- 必要な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants、OpenAI（および必要に応じて kabuステーション、Slack）の認証情報

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください）

---

## セットアップ手順（例）

1. リポジトリをクローン／配置
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - またはプロジェクト提供の requirements.txt / pyproject.toml からインストール
4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動的に読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨の `.env` に含める主要キー（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO
- OPENAI_API_KEY=sk-...

注意: OpenAIキーは各 ai モジュールで使用します（score_news / score_regime）。J-Quants は refresh token を用いて id token を取得します。

---

## 使い方（代表的な例）

以下は python モジュールを直接呼び出す最小例です。実行環境で環境変数や DuckDB ファイルパスを適切に設定してください。

- DuckDB 接続例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を省略すると今日が対象（カレンダー調整あり）
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI APIキーが環境変数 OPENAI_API_KEY にある前提）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
volatility = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

- 監査DBの初期化（監査テーブル作成）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存件数: {saved}")
```

---

## 設定と挙動の注意点

- 環境変数の自動読み込み
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の存在）を基準に .env と .env.local を自動で読み込みます。
  - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 読み込み優先度: OS 環境変数 > .env.local (上書き) > .env

- OpenAI 呼び出し
  - ai モジュール（news_nlp, regime_detector）は OpenAI の Chat Completions を JSON mode で利用します。API エラー時はフェイルセーフ（多くの場合 0.0 を返す）で稼働を継続します。
  - テスト時に API 呼び出しをモックできるよう設計されています（内部 _call_openai_api をパッチ可能）。

- J-Quants クライアント
  - レート制限を守るための RateLimiter、リトライ、401 のトークン自動リフレッシュを実装しています。
  - 取得データは fetched_at を UTC ISO 形式で付与して保存します（Look-ahead バイアス対策）。

- DuckDB 互換性
  - 一部の executemany / list バインドに関して DuckDB のバージョン差を考慮する実装が含まれます。

- 本番発注は実装範囲外
  - このライブラリはデータプラットフォーム・監査ログ・シグナル生成・スコアリング・ETL を提供しますが、実際のブローカー注文の送信・資金管理は個別実装が必要です。live 環境での運用は十分に検証してください（KABUSYS_ENV=live）。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py  — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 / 保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 他）
    - etl.py              — ETL 公開インターフェース (ETLResult)
    - calendar_management.py — マーケットカレンダー管理 / 判定ユーティリティ
    - news_collector.py   — RSS 収集（SSRF 対策・前処理）
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize 等）
    - audit.py            — 監査ログスキーマ初期化・DB初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / バリュー / ボラティリティ 等
    - feature_exploration.py — 将来リターン・IC・統計サマリ等

（実際のファイルは src/kabusys 以下に配置されています）

---

## 開発／テストヒント

- テスト／CI で .env 自動ロードを抑止したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分は内部の `_call_openai_api` をモックすることで外部依存を排除してユニットテストが可能です。
- DuckDB を使った単体テストでは `:memory:` を渡してインメモリ DB を利用できます（data.audit.init_audit_db などは ":memory:" サポートあり）。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt の推奨セット、あるいは具体的な CLI / systemd 起動例を追記します。どの情報を追加したいか教えてください。