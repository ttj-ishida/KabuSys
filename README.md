# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants 経由のデータ取得）、ニュース収集・NLP による銘柄スコア付与、研究用ファクター計算、監査ログ（トレーサビリティ）、市場カレンダー管理などを含みます。

---

## 主な特徴 (Features)

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、上場情報、JPX マーケットカレンダーを差分取得・保存
  - DuckDB に対する冪等保存（ON CONFLICT / upsert）
  - レートリミット・リトライ・トークン自動リフレッシュ対応

- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策・受信サイズ制限・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング（news_nlp）
  - マクロニュース + ETF（1321）200日移動平均乖離を合成して市場レジーム（bull/neutral/bear）判定（regime_detector）

- 研究（Research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリー、Zスコア正規化ユーティリティ

- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（quality モジュール）

- 監査ログ（Audit / Tracing）
  - シグナル → 発注 → 約定までの監査テーブル定義と初期化ユーティリティ
  - 発注の冪等キー（order_request_id）などを備えたトレーサビリティ

- 環境設定
  - .env / .env.local からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数は Settings 経由で明示的に参照

---

## セットアップ手順

前提:
- Python 3.8+（ソースで型ヒントに | 型が使われているため 3.10+ を想定する場合もあります）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```
   または pyproject.toml を使う場合は poetry / pip を利用してください。

2. 必要な Python パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - これらはプロジェクトの依存定義に含まれている想定です。必要に応じて pip install で追加してください。

3. 環境変数を用意する
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成すると、自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な必須環境変数
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabu ステーション API のパスワード（本ライブラリ内で参照）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   オプション
   - OPENAI_API_KEY — OpenAI を使う処理（news_nlp / regime_detector）の場合に必要。関数呼び出し時に api_key を明示的に渡すことも可能。
   - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
   - LOG_LEVEL — `DEBUG`, `INFO`, ...
   - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH — デフォルト `data/monitoring.db`

   注意: Settings は必須変数未設定時に ValueError を投げます。

4. データベース用ディレクトリ作成
   - デフォルトの DuckDB ファイルパス（settings.duckdb_path）が指す親ディレクトリを作成してください（多くの関数は自動作成しますが、外部ツールでの配置に注意）。

---

## 使い方（基本例）

以下は簡単な利用例です。DuckDB 接続を作成し、ETL や NLP、レジーム評価を呼び出します。

- 日次 ETL の実行例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DuckDB 接続（ファイル: settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))

# 今日の ETL（target_date を指定可能）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア付与（OpenAI API キーを環境変数にセットしている場合）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を用いて監査テーブルへアクセス可能
```

- 研究用関数（ファクター計算例）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄のファクター辞書のリスト
```

注意点:
- 各モジュールはバックテストにおけるルックアヘッドバイアスを避ける設計（現在時刻を直接参照しない）になっています。target_date を明示して利用してください。
- OpenAI 呼び出しは外部APIに依存するためレート制限や料金に注意してください。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み（.env / .env.local）と Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースを銘柄別に集約して OpenAI でスコア化する
    - regime_detector.py  — ETF 1321 の MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save系、認証・レート制御）
    - pipeline.py         — ETL パイプライン（run_daily_etl など）
    - etl.py              — ETL の公開型再エクスポート（ETLResult）
    - news_collector.py   — RSS 収集（SSRF 対策・前処理・保存）
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - stats.py            — zscore 正規化など統計ユーティリティ
    - quality.py          — データ品質チェック
    - audit.py            — 監査ログ（DDL・初期化）
  - research/
    - __init__.py
    - factor_research.py  — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — forward returns, IC, factor summary, rank
  - research/ 以下はバックテスト・研究用ユーティリティ群

---

## 環境変数の自動読み込みの挙動

- 起点はこのパッケージのファイル位置から親方向に .git または pyproject.toml を探索しプロジェクトルートを推定します。
- 自動読み込みの順序:
  1. OS 環境変数（既存）
  2. .env（プロジェクトルート）
  3. .env.local（上書き可能）
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## 注意事項 / ベストプラクティス

- OpenAI / J-Quants の API キーは厳重に管理してください。`.env` に直接コミットしないでください。
- ETL / API 呼び出しはネットワークや料金に依存します。ローカルテストではモックやレコードの最小化を推奨します。
- DuckDB のバージョン差異（executemany の挙動など）により注意点があります（パイプライン中に空パラメータの executemany を避ける等、コード内に対策あり）。
- 監査テーブルは削除しない前提です。運用時はバックアップ戦略を検討してください。

---

## ライセンス / 貢献

（このリポジトリに合わせて適宜記載してください）

---

README に不足している情報や、利用シナリオに合わせた具体的な例（例: バックテスト用のデータスナップショット作成、Slack 通知統合、kabu ステーションとの連携フローの例など）が必要であれば、目的に合わせて追記します。どの部分を詳しく説明しましょうか？