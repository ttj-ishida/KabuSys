# KabuSys

KabuSys は日本株向けの自動売買（アルゴリズム取引）システムの骨組み（スキャフォールド）です。  
データ取得（data）、売買戦略（strategy）、注文実行（execution）、監視（monitoring）といった主要コンポーネントをレイヤー化しており、独自のアルゴリズムや実行ロジックを組み込める構成になっています。

バージョン: 0.1.0

---

## 機能一覧（想定）

現在のリポジトリはパッケージ構成の雛形です。以下の機能を実装することを想定しています。

- data: 市場データ（板情報、約定履歴、ローソク足等）の取得・前処理API
- strategy: 取得したデータに基づく売買シグナル生成ロジック
- execution: ブローカー/API（例：kabuステーションなど）へ注文を送信・管理する機能
- monitoring: 稼働状況・パフォーマンスのログ化・可視化（メール／Slack通知等）

注意: 現在のコードベースは各モジュールのパッケージ化（__init__.py）までが用意された段階です。具体的な実装はこれから追加することを前提としています。

---

## セットアップ手順

1. 必要条件
   - Python 3.8 以上（プロジェクトのポリシーに応じて適宜変更してください）
   - git

2. リポジトリのクローン
```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

3. 仮想環境の作成（推奨）
```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

4. 依存パッケージのインストール  
   本リポジトリには requirements ファイルが用意されていないため、必要なライブラリ（例: requests, pandas, numpy 等）をプロジェクトに応じて追加してください。開発中は以下のようにセットアップ可能です（editable install）:
```bash
pip install -e .
# 必要なライブラリを個別にインストール
pip install requests pandas numpy
```

5. 環境変数・設定ファイル  
   ブローカーAPIキーや接続情報が必要な場合は、環境変数または設定ファイル（例: config.yaml / .env）で管理してください。実装例を作る際は `README` に具体的な設定方法を追記してください。

---

## 使い方（基本例）

以下はパッケージをインポートしてバージョンを確認する簡単な例です。

```python
import kabusys

print(kabusys.__version__)  # 0.1.0
```

想定するワークフロー（擬似コード）:

1. データ取得
```python
from kabusys.data import DataClient

data_client = DataClient(api_key="...")
prices = data_client.get_candles(symbol="7203", timeframe="1m")
```

2. 戦略でシグナル生成
```python
from kabusys.strategy import MyStrategy

strategy = MyStrategy(params={...})
signal = strategy.generate(prices)
```

3. 注文実行
```python
from kabusys.execution import ExecutionClient

exec_client = ExecutionClient(api_key="...")
if signal == "BUY":
    exec_client.send_order(symbol="7203", side="BUY", quantity=100)
```

4. 監視・通知
```python
from kabusys.monitoring import Monitor

monitor = Monitor()
monitor.log_trade({...})
monitor.notify("Order executed: BUY 7203")
```

上記のクラス・メソッドはサンプルであり、現時点では具体的な実装は含まれていません。実装時に API 仕様・メソッド名を定義してください。

---

## ディレクトリ構成

現在のプロジェクト構成（主要ファイルのみ）:

```
src/
└── kabusys/
    ├── __init__.py          # パッケージ情報（__version__ 等）
    ├── data/
    │   └── __init__.py      # データ取得関連モジュールを配置
    ├── strategy/
    │   └── __init__.py      # 戦略ロジックを配置
    ├── execution/
    │   └── __init__.py      # 注文実行ロジックを配置
    └── monitoring/
        └── __init__.py      # 監視・通知関連を配置
```

将来的に追加する想定ファイル例:
- src/kabusys/data/client.py
- src/kabusys/strategy/base.py、strategies/*.py
- src/kabusys/execution/broker_adapter.py
- src/kabusys/monitoring/logger.py、notifier.py

---

## 実装・拡張ガイド（簡潔）

- 各サブパッケージに対して明確なインターフェース（例: DataClient, StrategyBase, ExecutionAdapter, Monitor）を定義すると拡張しやすくなります。
- 外部APIとやり取りする部分は adapter 層として分離し、モックを用いたユニットテストが可能な設計にするのが望ましいです。
- リアルマネーでの運用前にペーパートレード・バックテスト機能を実装して十分な検証を行ってください。

---

## 貢献

- バグ報告、機能提案、プルリクエストは歓迎します。
- 大きな変更を行う場合は事前に Issue を立ててください。

---

必要であれば、README に具体的な API 例、設定ファイルテンプレート、テスト実行方法などを追記できます。どの部分を詳細化したいか教えてください。