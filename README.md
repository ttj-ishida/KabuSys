# KabuSys

日本株自動売買システム（KabuSys）の雛形パッケージです。  
このリポジトリは、データ取得、売買戦略、注文実行、監視の4つの主要コンポーネントを分離して実装できるようにした構成になっています。実際の取引ロジックやAPIクライアントは各サブパッケージに実装していく想定です。

---

## 概要

KabuSys は、日本株の自動売買システムを構築するためのプロジェクトのベースとなるパッケージ構成を提供します。以下のサブパッケージで機能を分割しています。

- data: 市場データの取得・整形（ヒストリカル、板情報など）
- strategy: 売買戦略（シグナル生成／ポジション管理）
- execution: 注文の発行・約定管理（ブローカーAPI連携）
- monitoring: 稼働監視・ログ・通知

パッケージバージョンは `kabusys.__version__` で確認できます（初期バージョンは 0.1.0）。

---

## 機能一覧（想定・雛形）

- 基本パッケージ構成（data / strategy / execution / monitoring）
- 各機能ごとに独立したモジュール配置を想定
- 開発者が各サブパッケージ内に実装を追加することで機能拡張可能
- テスト・CI・デプロイの追加に適した構成

> 注意: 本リポジトリは雛形であり、実際のデータ取得・注文送信の実装は含まれていません。実装は各サブパッケージに追加してください。

---

## 必要要件

- Python 3.8 以上を推奨
- 仮想環境（venv / virtualenv / pyenv-virtualenv 等）を利用することを推奨

（外部ライブラリはこの雛形内に requirements ファイルがないため、実装に応じて追記してください。）

---

## セットアップ手順

1. リポジトリをクローン／取得
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS / Linux:
   source .venv/bin/activate
   ```

3. 開発に必要なパッケージをインストール
   - この雛形には requirements ファイルが含まれていないため、必要に応じて `requirements.txt` や `pyproject.toml` を作成してからインストールしてください。
   - ローカルから開発インストールして動作確認する場合は、プロジェクトルートに `setup.py` または `pyproject.toml` を用意した上で以下を実行できます。
   ```
   pip install -e .
   ```
   - もしくは簡易的に Python のモジュール検索パスに `src` を追加して実行できます（開発段階での一時的な方法）:
   ```
   export PYTHONPATH=$PWD/src:$PYTHONPATH   # macOS / Linux
   set PYTHONPATH=%CD%\src;%PYTHONPATH      # Windows PowerShell 等
   ```

---

## 使い方（入門）

雛形の基本的なインポートとバージョン確認の例。

Python REPL またはスクリプト内で:
```python
import kabusys

print(kabusys.__version__)  # 例: "0.1.0"

# サブパッケージを参照
from kabusys import data, strategy, execution, monitoring
```

サブパッケージは現在空のパッケージ（プレースホルダ）です。以下は、各サブパッケージに実装を追加するための簡単な雛形例です（実際のAPIやロジックはプロジェクトに応じて実装してください）。

- data の雛形例
```python
# src/kabusys/data/market.py
class MarketDataClient:
    def get_ticker(self, symbol: str):
        # 実装例: 外部APIから終値・板・出来高などを取得して返す
        raise NotImplementedError
```

- strategy の雛形例
```python
# src/kabusys/strategy/simple.py
class SimpleStrategy:
    def __init__(self, data_client):
        self.data_client = data_client

    def decide(self, symbol: str):
        # 実装例: シグナルを生成して 'buy' / 'sell' / 'hold' を返す
        return "hold"
```

- execution の雛形例
```python
# src/kabusys/execution/client.py
class ExecutionClient:
    def send_order(self, symbol: str, side: str, qty: int):
        # 実装例: ブローカーAPIに注文を送る
        raise NotImplementedError
```

- monitoring の雛形例
```python
# src/kabusys/monitoring/logging.py
def notify(message: str):
    # 実装例: ログ出力、メール、Slack通知など
    print(message)
```

これらを組み合わせて簡単なワークフロー（データ取得 → 戦略判断 → 注文発行 → 監視）を作ることができます。

---

## ディレクトリ構成

リポジトリ内の現状のファイル構成（抜粋）は以下の通りです。

- src/
  - kabusys/
    - __init__.py                # パッケージのエントリポイント（バージョンなど）
    - data/
      - __init__.py
      # - market.py  (ここに実装を追加)
    - strategy/
      - __init__.py
      # - simple.py  (ここに実装を追加)
    - execution/
      - __init__.py
      # - client.py  (ここに実装を追加)
    - monitoring/
      - __init__.py
      # - logging.py (ここに実装を追加)

README や設定ファイル、テスト、ドキュメント等はプロジェクトのルートに配置してください。

---

## 開発ガイド / 推奨事項

- 各サブパッケージは責務を分けて実装する（単一責任の原則）。
- 外部APIキーやシークレットは環境変数やシークレット管理ツールで管理する（コードベースに直接書かない）。
- 注文の実行部分はテスト／シミュレーションモードを用意して、実運用前に十分に検証する。
- ロギングと監視を充実させ、異常時のアラートを必ず設定する。
- 単体テストと統合テストを用意して、自動化（CI）を行う。

---

この README は雛形パッケージ向けの説明です。実際の取引システムとして運用する際は、金融商品取引法や各ブローカーの利用規約を遵守し、十分なテストを行ってください。