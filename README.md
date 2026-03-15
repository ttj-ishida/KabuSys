# KabuSys

KabuSysは日本株向けの自動売買（アルゴリズムトレーディング）システムの土台（スケルトン）です。本リポジトリはモジュール分割（データ取得、戦略、発注、監視）を想定したパッケージ構成を提供し、実装を追加していくための出発点になります。

バージョン: 0.1.0

---

## 概要

このプロジェクトは、以下の責務を分離した自動売買システムの雛形です。

- data: 市場データ（板情報・約定・株価など）の取得／管理
- strategy: 売買ロジック（エントリー／イグジット）の実装
- execution: 証券会社APIへの注文発行や約定管理
- monitoring: 稼働状況の監視・ログ・通知

現時点では各パッケージは空のモジュール（骨組み）になっており、これらに具象実装を追加していく想定です。

---

## 機能一覧（想定・拡張ポイント）

- 市場データの収集・キャッシュ（data）
- 戦略の定義とシグナル生成（strategy）
- 注文発行・注文管理（execution）
- 稼働状態・損益・アラートの監視（monitoring）
- 各モジュールの差し替え・テスト用モックの導入が容易な構造

※ 実際のAPI連携や戦略は含まれていません。用途に応じて実装してください。

---

## セットアップ手順

1. システム要件
   - Python 3.8 以上（推奨）
   - 仮想環境の利用を推奨（venv, pyenv, conda など）

2. リポジトリをクローン
   - git clone で取得してください

3. 仮想環境作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存パッケージのインストール
   - 現状は必須依存はありません。必要に応じて`requirements.txt`や`pyproject.toml`を作成して管理してください。
   - ローカル開発としてパッケージをインストールする場合:
     - pip install -e .  （プロジェクトルートに pyproject.toml または setup.py が必要です）
   - 代替として、プロジェクトルートをPYTHONPATHに追加して利用できます。

5. 動作確認（簡易）
   - Python REPLやスクリプトでバージョン確認:
     - python -c "import kabusys; print(kabusys.__version__)"

---

## 使い方（拡張・利用例）

現状はモジュールの雛形のみですが、以下のように実装・利用していきます。

1. データプロバイダ（例）
   - src/kabusys/data/provider.py を作成し、APIクライアントやデータ取得ロジックを実装します。

例: data/provider.py（雛形）
```
class DataProvider:
    def get_price(self, symbol: str) -> float:
        """指定銘柄の最新価格を返す（実装例）"""
        raise NotImplementedError
```

2. 戦略（例）
   - src/kabusys/strategy/simple.py に戦略ロジックを実装します。

例: strategy/simple.py（雛形）
```
class SimpleStrategy:
    def __init__(self, data_provider):
        self.data = data_provider

    def should_buy(self, symbol: str) -> bool:
        # シグナル生成ロジックを実装
        raise NotImplementedError
```

3. 発注（execution）と統合
   - execution/order_manager.py に注文を出すクラスを実装し、戦略のシグナルを受けて発注します。

例: execution/order_manager.py（雛形）
```
class OrderManager:
    def send_order(self, symbol: str, side: str, size: int):
        """証券会社APIへ注文を送信"""
        raise NotImplementedError
```

4. 監視（monitoring）
   - monitoring/logger.py などでログ・アラートを実装します。

5. 簡単な実行フロー（擬似コード）
```
from kabusys.data.provider import DataProvider
from kabusys.strategy.simple import SimpleStrategy
from kabusys.execution.order_manager import OrderManager
from kabusys.monitoring.logger import Logger

data = DataProvider(...)
strategy = SimpleStrategy(data)
orders = OrderManager(...)
logger = Logger(...)

symbol = "7203.T"
if strategy.should_buy(symbol):
    orders.send_order(symbol, side="BUY", size=100)
    logger.info("Bought 100 shares of " + symbol)
```

上記は実装例のひな型です。各クラスのインターフェースはプロジェクトの要件に合わせて設計してください。

---

## ディレクトリ構成

現在の主要ファイル／ディレクトリ構成は以下です。

- src/
  - kabusys/
    - __init__.py         (パッケージ初期化、バージョン情報)
    - data/
      - __init__.py       (データ関連モジュール置き場)
    - strategy/
      - __init__.py       (戦略関連モジュール置き場)
    - execution/
      - __init__.py       (発注関連モジュール置き場)
    - monitoring/
      - __init__.py       (監視関連モジュール置き場)

今後、各サブパッケージ内に具象実装ファイル（provider.py、simple.py 等）を追加していきます。

---

## 開発のヒント

- 各モジュールはインターフェース（抽象クラスやプロトコル）を先に定義し、テスト用のモック実装を用意すると実装と検証が楽になります。
- 実際の発注を行うexecution部分は必ずテストモードやサンドボックスで十分に検証してください。市場リスクがあります。
- 機密情報（APIキー等）は環境変数やシークレット管理を用いて管理してください。

---

## 貢献・ライセンス

- 貢献歓迎。Pull RequestやIssueを送ってください。
- ライセンスファイル（LICENSE）はプロジェクトルートに追加してください（例: MIT License）。

---

このREADMEは現状のコードベース（モジュール雛形）に基づくものです。具体的なAPI連携や戦略実装は追加実装により拡張してください。必要であれば、テンプレート実装や具体的なサンプルを追加して README を拡張します。希望があれば教えてください。