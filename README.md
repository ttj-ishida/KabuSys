# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（OpenAI を利用）による銘柄センチメント、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを含みます。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 差分更新、ページネーション、トークン自動リフレッシュ、レートリミット、リトライ対応
- データ品質チェック
  - 欠損、主キー重複、株価スパイク、将来日付・非営業日の検出
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去など）と前処理
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント付与（ai_scores への書き込み）
  - マクロニュース + ETF（1321）200 日移動平均乖離を合成した市場レジーム判定（bull/neutral/bear）
  - API 呼び出しのリトライ・フェイルセーフ（失敗時は中立スコア）
- リサーチ機能
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化、統計サマリー
- 監査ログ（Audit）
  - signal_events、order_requests、executions テーブルを用いたトレーサビリティ構築
  - 監査用 DuckDB データベース初期化ユーティリティ

---

## 要件

- Python 3.10+（型ヒントに Python 3.10 の union 表記を想定）
- ランタイム依存（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード）

※ プロジェクトに requirements.txt / pyproject.toml があればそちらを優先してください。

---

## セットアップ手順

1. リポジトリをクローン（省略）
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（macOS / Linux）
   - .\.venv\Scripts\activate（Windows）
3. パッケージのインストール（開発モード推奨）
   - pip install -e .
   - または必要パッケージを個別インストール:
     - pip install duckdb openai defusedxml
4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると自動で読み込まれます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（最低限必要なキー）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- KABU_API_PASSWORD=...（kabu ステーション連携が必要な場合）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

注意: Settings は不足している必須環境変数を取得すると ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

---

## 使い方（クイックスタート）

以下は代表的なユースケースの最小例です。実際はログ設定やエラーハンドリングを追加してください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- AI ニューススコア（銘柄別）を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("written:", n_written)
```

- 市場レジーム判定を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査ログを書き込む
```

- RSS フィードを取得する（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

for source, url in DEFAULT_RSS_SOURCES.items():
    articles = fetch_rss(url, source)
    # raw_news テーブルへの保存や news_symbols の紐付けは別途実装（プロジェクトの DB スキーマに合わせて挿入）
```

---

## 環境変数と設定の詳細

- 自動 .env ロード順序（優先度高 → 低）
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env（存在すれば未設定のキーをセット）

- 自動ロード無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします（テスト等で便利）。

- 主要な環境変数（Settings で参照）
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
  - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
  - SLACK_BOT_TOKEN (必須) — Slack 通知用
  - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
  - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH (任意) — 監視系などで使用: data/monitoring.db
  - KABUSYS_ENV (任意) — development / paper_trading / live（検証あり）
  - LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL
  - OPENAI_API_KEY — OpenAI 呼び出しで使用（score_news, regime_detector）

---

## よくあるトラブルシューティング

- ValueError: 環境変数が設定されていません
  - Settings のプロパティが必須キーにアクセスした際に発生します。`.env` に必要なキーを追加するか環境変数を設定してください。
- DuckDB ファイルの親ディレクトリが無い
  - init_audit_db や settings.duckdb_path を使う際、親ディレクトリは自動作成しますが、パーミッションなど注意してください。
- OpenAI / J-Quants API エラー
  - リトライやフェイルセーフは組み込まれていますが、APIキーの有効性、レート制限、ネットワークの安定性を確認してください。
- RSS の取得で SSRF / private host の検出
  - news_collector は意図的に内部アドレスや非 http(s) スキームをブロックします。外部公開 URL を使用してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン定義
  - config.py — 環境変数 / 設定管理（.env 自動読込・Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース記事の OpenAI による銘柄別スコア化（ai_scores 書き込み）
    - regime_detector.py — ETF（1321）MA 乖離 + マクロニュースを用いた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ含む）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - etl.py — ETLResult の公開エイリアス
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - stats.py — z-score 正規化など統計ユーティリティ
    - quality.py — データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py — 監査ログスキーマ定義・初期化ユーティリティ
    - news_collector.py — RSS 収集と前処理（SSRF 対策等）
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - その他（strategy, execution, monitoring 等のサブパッケージは __all__ で公開される想定）

---

## 開発・貢献

- テストや CI はこの README に含まれていません。ユニットテストを書く際は、OpenAI / ネットワーク呼び出しはモック（patch）することを推奨します。ソース中にも _call_openai_api の差し替えを想定した記述があり、テスト容易性に配慮したデザインです。
- 外部 API 呼び出し（J-Quants / OpenAI / RSS）はネットワークの副作用があるため、ユニットテストではモックしてください。

---

以上がプロジェクトの概要と基本的な使い方です。README の補足やサンプルスクリプトが必要であれば、どのワークフロー（例: 完全な ETL バッチスクリプト、ニュース収集→DB 保存の例、戦略から発注までの監査ログ化例）を追加したいか教えてください。