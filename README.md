# KabuSys

日本株自動売買システムのための軽量フレームワーク（スケルトン実装）

バージョン: 0.1.0

このリポジトリは、「データ取得」「ストラテジー」「注文実行」「モニタリング」を分離した構成で日本株の自動売買システムを構築するための骨組み（パッケージ構成）を提供します。実際の取引ロジックやAPI連携は含まれておらず、拡張して利用することを想定しています。

---

## 機能一覧

- パッケージ化されたモジュール構成
  - data: 市場データやティッカー情報の取得を担当するレイヤ
  - strategy: 売買戦略（アルゴリズム）を実装するレイヤ
  - execution: 発注や約定管理を行うレイヤ（ブローカAPI連携部分）
  - monitoring: ログや通知、ダッシュボード連携などの監視機能用レイヤ
- 軽量スケルトン実装により、独自の戦略・実装を容易に追加可能
- パッケージメタ情報（バージョン）が設定済み

---

## 動作環境（例）

- Python 3.8 以上推奨
- OS: 特に依存なし（APIクライアント等を使う場合は別途要件あり）

実際のブローカAPI（例: kabuステーションなど）を利用する場合は、そのAPIクライアントや認証情報が別途必要になります。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt が無い場合は、使用するライブラリ（requests、pandas、websocket-client など）を必要に応じてインストールしてください。
   ```
   pip install -r requirements.txt
   ```

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```
   ※ プロジェクトに setup.py / pyproject.toml がある場合。無い場合はルートから Python の import パスを通す（PYTHONPATH を設定）か、開発環境から src ディレクトリを参照してください。

5. 実運用時は、ブローカーのAPIキーや認証情報を環境変数や設定ファイルで安全に管理してください。

---

## 使い方（基本例）

パッケージのバージョン確認・インポートの例:
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

モジュールの基本的な役割（例示コード／インターフェース案）:

- data レイヤ例（インターフェース）
```python
class DataProvider:
    def fetch_latest_price(self, symbol: str) -> float:
        """最新価格を返す"""
        raise NotImplementedError
```

- strategy レイヤ例
```python
class Strategy:
    def on_tick(self, price: float):
        """ティック毎に呼ばれ、売買判断を行う"""
        raise NotImplementedError

    def decide(self) -> dict:
        """売買アクション（例: {'side': 'BUY', 'qty': 100}）を返す"""
        raise NotImplementedError
```

- execution レイヤ例
```python
class Executor:
    def send_order(self, symbol: str, side: str, qty: int):
        """ブローカーAPIに注文を送る"""
        raise NotImplementedError
```

- monitoring レイヤ例
```python
class Monitor:
    def notify(self, message: str):
        """メールやSlack等に通知する"""
        raise NotImplementedError
```

これらのクラスを継承して実装し、アプリケーションのメインループで連携させることで自動売買システムが構築できます。

簡単な統合イメージ:
```python
from kabusys.data import MyDataProvider
from kabusys.strategy import MyStrategy
from kabusys.execution import MyExecutor
from kabusys.monitoring import MyMonitor

data = MyDataProvider(...)
strategy = MyStrategy(...)
executor = MyExecutor(...)
monitor = MyMonitor(...)

price = data.fetch_latest_price("7203.T")  # 銘柄コード例
strategy.on_tick(price)
action = strategy.decide()
if action:
    executor.send_order("7203.T", action['side'], action['qty'])
    monitor.notify(f"Ordered: {action}")
```

---

## ディレクトリ構成

現在の主要ファイル/ディレクトリ（スケルトン）:
```
src/
  kabusys/
    __init__.py            # パッケージ初期化、__version__ 等
    data/
      __init__.py
      # データ取得クラス等を追加
    strategy/
      __init__.py
      # ストラテジークラス等を追加
    execution/
      __init__.py
      # 発注・実行クラス等を追加
    monitoring/
      __init__.py
      # 監視・通知クラス等を追加
```

ルートには setup.py / pyproject.toml / requirements.txt を追加することを推奨します。

---

## 開発・拡張ガイド（推奨）

- 各レイヤは単一責務（Single Responsibility）に従って実装する
  - data: API呼び出し、キャッシュ、整形
  - strategy: シグナル生成（テストが書きやすい純粋関数化推奨）
  - execution: 送受注、エラーハンドリング、リトライ
  - monitoring: ログ集約、通知、メトリクス公開
- 単体テストと統合テストを用意する（pytest 等）
- 本番接続時はモックエクスキュータやサンドボックス環境で十分に検証する
- 機密情報（APIキー等）は環境変数やシークレット管理により保護する

---

必要であれば、テンプレートの実装例やCI設定、テストサンプルなどの追加を作成できます。どの部分を拡張したいか教えてください。