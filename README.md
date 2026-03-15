# KabuSys

KabuSys は日本株の自動売買システムの骨組みを提供する Python パッケージです。データ取得、売買戦略、注文実行、監視（ログ／メトリクス）という 4 つの主要コンポーネントをサブパッケージとして分離しており、各コンポーネントを実装・拡張して自動売買システムを構築できます。

現在はパッケージの骨組み（スケルトン）としての実装で、プロジェクト固有のロジック（データソースやAPI連携、実行ロジックなど）を追加して利用します。

バージョン: 0.1.0

---

## 機能一覧

- プロジェクト構造の提供
  - data: 市場データ取得／管理のための拡張ポイント
  - strategy: 売買戦略の実装場所
  - execution: 注文送信・約定管理の実装場所
  - monitoring: ログ記録・監視／アラート実装場所
- 軽量で拡張しやすい設計（サブパッケージを自由に実装して利用）
- パッケージメタ情報によりバージョン確認が可能（kabusys.__version__）

> 注意: 現在はインターフェースの雛形のみであり、個別の機能（APIクライアントやトレードロジック等）は含まれていません。実際の売買を行う前に、十分な実装と検証を行ってください。

---

## 要件

- Python 3.8 以上（プロジェクト方針に合わせて調整してください）
- 必要な外部ライブラリはプロジェクトで追加してください（例: requests、pandas、websocket-client など）

（補足）依存ライブラリの固定は `pyproject.toml` や `requirements.txt` を作成して管理してください。

---

## セットアップ手順

ローカルで開発／利用する一般的な手順の例を示します。

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

2. 仮想環境の作成（推奨）
   - venv を使う例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

3. 開発インストール（編集可能な状態でインストール）
   ```
   pip install -e .
   ```
   ※ setup.py / pyproject.toml が整備されている前提です。ない場合はパッケージフォルダを PYTHONPATH に含めるか、直接プロジェクトルートから実行してください。

4. 依存ライブラリのインストール
   ```
   pip install -r requirements.txt
   ```
   （requirements.txt を用意している場合）

---

## 使い方（基本）

パッケージはサブパッケージ群を提供します。まずはバージョン確認やモジュールのインポートができます。

例: バージョン確認
```python
import kabusys
print(kabusys.__version__)  # -> "0.1.0"
```

サブパッケージのインポート例:
```python
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring
```

各サブパッケージは空の __init__.py（拡張ポイント）で用意されています。実際の機能はプロジェクトで以下のように実装・追加してください。

- data: 市場データ（株価、出来高、板情報など）の取得クラス／関数を実装
  - 例: DataProvider クラス（OHLC取得、過去データのキャッシュ等）
- strategy: 売買戦略のクラスを実装
  - 例: StrategyBase を継承して、on_bar / on_tick / decide_order などを実装
- execution: 注文送信や注文管理（取消／約定監視）を実装
  - 例: ExecutionClient（API トークン管理、注文送信、注文状態取得）
- monitoring: ロギング、メトリクス送信、アラート（メール／Slack）などを実装

簡単な擬似コード（実装例の雛形）:
```python
# my_strategy.py (プロジェクト側で実装)
from kabusys import data, strategy, execution, monitoring

class MyStrategy:
    def __init__(self, data_provider, exec_client, monitor):
        self.data = data_provider
        self.exec = exec_client
        self.monitor = monitor

    def on_new_bar(self, bar):
        # ここで売買判断
        if self.should_buy(bar):
            self.exec.send_order(symbol=bar.symbol, side="BUY", qty=100)
            self.monitor.info(f"Bought {bar.symbol}")

    def should_buy(self, bar):
        # 具体的なロジックを実装
        return False
```

上記はあくまで一例です。実際には接続先 API（kabuステーション、証券会社API等）、認証情報、リスク管理、テスト手順を適切に構築してください。

---

## ディレクトリ構成

リポジトリ（例）の最小構成を示します。

- src/
  - kabusys/
    - __init__.py           # パッケージメタ情報（__version__ など）
    - data/
      - __init__.py         # データ関連の拡張ポイント
    - strategy/
      - __init__.py         # 戦略関連の拡張ポイント
    - execution/
      - __init__.py         # 注文実行関連の拡張ポイント
    - monitoring/
      - __init__.py         # 監視／ログ関連の拡張ポイント

現状のファイル:
- src/kabusys/__init__.py
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 開発・拡張ガイド

- インターフェース設計: 各サブパッケージに「インターフェース（抽象クラス）」を定義するとテストや差し替えが容易になります（例: DataProviderBase, StrategyBase, ExecutionClientBase）。
- テスト: ユニットテストを整備して、注文ロジックやリスク管理ロジックの検証を行ってください（pytest 推奨）。
- ロギング/監視: 実運用では詳細なログとアラートを整備し、異常時に自動停止する仕組みを導入してください。
- セキュリティ: API トークンや認証情報は環境変数やシークレットマネージャで管理し、ソース管理に含めないでください。
- 本番運用前の注意: 実資金を投入する前に、ペーパートレードや過去データによるバックテストで十分な検証を行ってください。

---

## 貢献・問い合わせ

- プロジェクトに改善や機能追加を行う場合は、Issue / Pull Request を作成してください。
- 危険を伴う実装（自動売買ロジック）に関しては、設計レビューと十分なテストを推奨します。

---

この README はプロジェクトの雛形に基づいて作成しました。実装内容や運用ポリシーに応じて適宜更新してください。