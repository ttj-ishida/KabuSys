# KabuSys

日本株向けの自動売買システム用ライブラリ（骨組み）。  
このリポジトリは、データ取得、戦略ロジック、注文実行、監視の役割を分離したパッケージ構成を提供します。実運用に合わせて各モジュールにロジックを実装して利用してください。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のための最小限の骨組みです。モジュールを分離することで、以下の役割を明確に実装・テストできます。

- data: 市場データの取得・加工
- strategy: 投資・売買戦略の実装
- execution: 注文送信・約定管理（ブローカーAPI連携）
- monitoring: ログ、状態監視、アラート、メトリクス

本パッケージはテンプレートとして提供しているため、実際のブローカーAPI（例: kabuステーション / 各種証券API）やデータソースと接続する実装は各自で追加してください。

---

## 機能一覧（想定）

- 市場データ取得の抽象化（リアルタイム／過去データ）
- 戦略ロジックのプラグイン化（複数戦略の切替可）
- 注文実行・約定管理（同期／非同期）
- 稼働状態の監視とログ出力
- 細かい実装を行うためのモジュール分割（拡張性重視）

※ 現状は骨組み（パッケージ構成）のみで、具体的な実装は含まれていません。各モジュールに必要なクラス／関数を追加してください。

---

## セットアップ手順

動作環境の一例:

- Python 3.8 以上（可能であれば最新の安定版を推奨）
- 仮想環境（venv、pyenv など）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成と有効化（例: venv）
   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 依存関係のインストール  
   現状 requirements.txt / pyproject.toml が含まれていない場合は、必要なライブラリ（requests, websockets, pandas, numpy, aiohttp など）をプロジェクトに応じて追加してください。例:
   ```
   pip install requests pandas numpy
   ```

4. 開発中にパッケージとして扱う方法
   - PYTHONPATH を使って実行（開発中に手軽）
     ```
     # プロジェクトルートで
     export PYTHONPATH=./src
     python examples/run_strategy.py
     ```
   - パッケージとしてインストール（pyproject.toml / setup.py を用意した場合）
     ```
     pip install -e .
     ```

5. 環境変数／シークレット
   ブローカーAPIや認証情報を扱う場合は環境変数や .env ファイルで管理してください。例:
   - KABU_API_KEY
   - KABU_API_SECRET
   - KABU_ENDPOINT

---

## 使い方（例）

各モジュールは現状プレースホルダです。おおまかな利用例（擬似コード）:

- 直接インポートして組み合わせる例
```python
# examples/run_strategy.py （例）
from kabusys import data, strategy, execution, monitoring

# 各モジュールに実装したクラスを使う想定
# 例: data.MarketClient, strategy.MyStrategy, execution.OrderExecutor, monitoring.Monitor

# market = data.MarketClient(api_key=..., endpoint=...)
# strat = strategy.MyStrategy(params=...)
# executor = execution.OrderExecutor(api_credentials=...)
# monitor = monitoring.Monitor(log_level="INFO")

# フロー（概念）
# 1) 市場データ取得
# ticks = market.get_realtime_ticks(symbol="7203")  # トヨタ自動車など

# 2) 戦略判定
# decision = strat.evaluate(ticks)

# 3) 注文実行
# if decision.should_buy:
#     executor.place_order(symbol="7203", side="BUY", size=decision.size)

# 4) 監視・ログ
# monitor.record(decision, ticks)
```

- 簡単なバージョン確認
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

注意:
- 実注文を送る前に、ペーパートレードやサンドボックス環境で十分に検証してください。
- マルチスレッド／非同期処理を行う場合は、注文の重複や競合に注意してください。

---

## ディレクトリ構成

現在のファイル／ディレクトリ構成（抜粋）:
```
repo-root/
├─ src/
│  └─ kabusys/
│     ├─ __init__.py         # パッケージ定義（バージョン等）
│     ├─ data/
│     │  └─ __init__.py      # 市場データ関連（実装追加）
│     ├─ strategy/
│     │  └─ __init__.py      # 戦略ロジック（実装追加）
│     ├─ execution/
│     │  └─ __init__.py      # 注文実行・ブローカー連携（実装追加）
│     └─ monitoring/
│        └─ __init__.py      # ログ・監視関連（実装追加）
```

推奨で追加するファイル例:
- examples/run_strategy.py（実行例スクリプト）
- requirements.txt
- pyproject.toml / setup.cfg / setup.py（パッケージ化用）
- .env.example（必要な環境変数のサンプル）
- docs/（詳細ドキュメント）

---

## 実装のヒント・注意点

- 接続先APIの仕様（認証方式、レートリミット、注文キャンセルの扱い）を十分に確認してください。
- 戦略ロジックは単体テストを書き、想定外入力（欠損データ、APIの遅延など）に対する堅牢性を確保してください。
- 取引は必ずリスク管理（最大損失、ポジションサイズ、スリッページ想定）を組み込んでください。
- ロギングや永続化（注文履歴、約定ログ）はトラブルシュートのために重要です。
- 本番運用前にペーパートレードで長時間の耐久テストを行ってください。

---

## 貢献・拡張

- 新しいデータソースやブローカーのクライアントを `data/` または `execution/` に追加してください。
- 戦略は `strategy/` にプラグイン形式で追加し、共通インターフェース（例: evaluate メソッド）を定義すると切替が容易になります。
- 監視はメトリクス送信（Prometheus など）やアラート通知（Slack, Email）を実装すると良いです。

---

この README は骨組みの説明です。実運用に合わせて各モジュールに具体的な実装とテストを追加してください。必要であれば README を拡張して、各モジュールの API ドキュメントや使用例を詳細に記載していくことをおすすめします。