# KabuSys

日本株自動売買システム（KabuSys）は、戦略（Strategy）・データ取得（Data）・注文実行（Execution）・監視（Monitoring）を分離したモジュール構成で、アルゴリズム取引の実装と実行を容易にするための骨組み（スケルトン）です。本リポジトリはフレームワークのベースを提供します。各モジュールに具体的な実装（銘柄データ取得、取引所API連携、売買ロジックなど）を追加して利用してください。

バージョン: 0.1.0

---

## 主な特徴

- モジュール化されたパッケージ構造
  - data: 市場データ取得・加工
  - strategy: 売買戦略ロジック
  - execution: 注文送信・約定処理
  - monitoring: ログ・メトリクス・アラート
- 開発用のシンプルな骨組みを提供し、独自の戦略を容易に追加可能
- テストやデプロイのための拡張ポイントを明確化

---

## 機能一覧（予定 / 想定）

- リアルタイム・ヒストリカルデータの取得モジュール（data）
- 戦略定義用のインターフェース（strategy）
- 注文管理・リスク管理（execution）
- 監視ダッシュボードやアラート（monitoring）
- 簡易的なバックテスト基盤（将来的に追加）

現在のリポジトリは「骨組み」です。各機能の実装はプロジェクトに合わせて追加してください。

---

## 動作環境 / 必要条件

- Python 3.8+
- git（ソース取得用）
- 実際の取引に接続する場合は、各取引所APIの利用環境／資格情報が必要

依存ライブラリは実装内容に応じて追加してください（例: requests, websockets, pandas, numpy など）。

---

## セットアップ（開発環境向け）

1. リポジトリをクローン
   - git clone を行ってください。

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 開発インストール
   - プロジェクトルートに `setup.py` または `pyproject.toml` を配置している前提で:
     - pip install -e .
   - もしパッケージ配備用の設定が無い場合は、開発中はプロジェクトのルートを PYTHONPATH に追加してインポートできます。
     - export PYTHONPATH=$(pwd)/src:$PYTHONPATH  （Windows は適宜置換）

4. 依存ライブラリのインストール（任意）
   - pip install pandas requests websocket-client など、実装に応じて必要なパッケージを追加

---

## 使い方（基本例）

このパッケージは骨組みのみのため、実際のロジックを実装して使います。以下は利用方法の一例（実装例）です。

1. strategy に戦略クラスを作る（例: src/kabusys/strategy/my_strategy.py）

```python
# src/kabusys/strategy/my_strategy.py
from kabusys import __version__

class MyStrategy:
    def __init__(self, config):
        self.config = config

    def on_market_data(self, data):
        # データに基づいて売買判断を行う
        # True -> 買い, False -> 売り, None -> 何もしない など
        pass

    def on_order_update(self, order):
        # 注文状態更新のハンドリング
        pass
```

2. execution に注文送信ロジックを実装する（例: src/kabusys/execution/api_client.py）

```python
# src/kabusys/execution/api_client.py
class ExecutionClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def send_order(self, symbol, side, size, price=None):
        # 実際のAPI呼び出しを実装
        pass

    def cancel_order(self, order_id):
        pass
```

3. data から市場データを供給し、strategy と execution を組み合わせて運用するランナーを作る

```python
# run.py (プロジェクトルート)
from kabusys.strategy.my_strategy import MyStrategy
from kabusys.execution.api_client import ExecutionClient
from kabusys.data import ...  # 実装に合わせて

def main():
    config = {...}
    strat = MyStrategy(config)
    client = ExecutionClient(api_key="YOUR_API_KEY")
    # データ取得ループの中で strat.on_market_data を呼び、
    # 戦略が注文を返したら client.send_order を呼ぶ、など

if __name__ == "__main__":
    main()
```

---

## 設定（例）

- APIキーや環境設定は、環境変数または設定ファイル（YAML/JSON）で管理することを推奨します。
- 例: 環境変数
  - KABU_API_KEY
  - KABU_API_SECRET

---

## ディレクトリ構成

現状の構成は以下の通りです（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py
    - data/
      - __init__.py
      - (データ取得モジュールをここに追加)
    - strategy/
      - __init__.py
      - (戦略モジュールをここに追加)
    - execution/
      - __init__.py
      - (注文実行モジュールをここに追加)
    - monitoring/
      - __init__.py
      - (監視・ロギング関連をここに追加)

ルート（プロジェクトルート）に README.md、必要に応じて pyproject.toml / setup.py、requirements.txt を配置してください。

---

## コントリビュート

- 機能追加、バグ修正、ドキュメント改善は歓迎します。
- プルリクエスト前に Issue を立て、変更内容を共有してください。
- 実装時はユニットテストを追加することを推奨します。

---

## 注意事項

- 本リポジトリは取引機能の「骨組み」です。実運用で使用する前に、十分なテストと監査を行ってください。
- 実際の売買を行う場合、APIキーやシークレットの管理、接続時のエラーハンドリング、リスク管理（資金管理・最大ドローダウン制御など）を必ず実装してください。
- 取引に伴う損失に関して、このリポジトリは責任を負いません。

---

必要であれば、戦略インターフェースの雛形やサンプル実装、簡易バックテストスクリプトなどの追加ドキュメントを作成します。どの部分の例が欲しいか教えてください。