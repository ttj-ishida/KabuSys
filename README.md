# KabuSys — 日本株自動売買システム

KabuSys は日本株の自動売買システム向けの軽量なパッケージ構成（スケルトン）です。マーケットデータ取得、売買戦略、発注・実行、監視の責務を分離して管理できるようにディレクトリを分けた設計を想定しています。本リポジトリは骨組み（テンプレート）として提供され、ここに各機能の実装を追加していきます。

バージョン: 0.1.0

---

## 機能一覧（想定）

- data: 市場データの取得・保存・前処理（ヒストリカル、リアルタイム）
- strategy: 売買戦略の実装レイヤ（シグナル生成、ポジション管理）
- execution: ブローカー（API）への発注・注文管理・約定処理
- monitoring: ログ、メトリクス、可視化、アラート

> 注: 現在のリポジトリはパッケージ構成のみを提供しています。上記機能は各モジュールに実装していく想定です。

---

## セットアップ手順

必要条件
- Python 3.8 以上（推奨は 3.8〜3.11）
- Git

ローカル開発の基本手順（パッケージ化設定がない場合も動作する例を含む）:

1. リポジトリをクローン
   ```
   git clone <リポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成・有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要な依存がある場合は `requirements.txt` からインストール（依存ファイルがない場合はスキップ）
   ```
   pip install -r requirements.txt
   ```

4. ローカル開発時にパッケージを使う方法
   - プロジェクトをパッケージとしてインストールする場合（setup/pyproject が整備されていれば）:
     ```
     pip install -e .
     ```
   - まだパッケージ化していない場合は PYTHONPATH を通す:
     - macOS / Linux:
       ```
       export PYTHONPATH=$(pwd)/src
       python -c "import kabusys; print(kabusys.__version__)"
       ```
     - Windows:
       ```
       set PYTHONPATH=%cd%\src
       python -c "import kabusys; print(kabusys.__version__)"
       ```

---

## 使い方（例）

まずはパッケージが正しくインポートできるか確認します。

```
python -c "import kabusys; print(kabusys.__version__)"
```

モジュールのインポート例:

```python
from kabusys import data, strategy, execution, monitoring

# それぞれのモジュールに実装を追加して利用する想定です
```

戦略や実行の骨組み（例、実装はユーザーが追加）:

```python
# strategy/example_strategy.py
class ExampleStrategy:
    """
    簡単な戦略の雛形
    - on_tick: 新しい市場データを受け取った際に呼び出される
    - decide: シグナルを生成する（買い/売り/待機）
    """
    def on_tick(self, market_data):
        signal = self.decide(market_data)
        return signal

    def decide(self, market_data):
        # ユーザー実装: 単純移動平均等を計算してシグナルを返す
        return "HOLD"  # または "BUY", "SELL"
```

発注の呼び出し（execution モジュールに実装を追加）:

```python
# 実行は execution モジュールで行います（実装はプロジェクト側で追加）
from kabusys import execution

# 仮の API
# execution.place_order(symbol="7203.T", side="BUY", size=100, price=None)
```

監視（monitoring）やログも同様にモジュール側で実装を追加していきます。

---

## ディレクトリ構成

現在の最小構成（ファイル一覧）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージのメタ情報（バージョン等）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
```

各ディレクトリの役割:
- src/kabusys/__init__.py: パッケージのエントリ（バージョン、公開 API 等）
- src/kabusys/data: 市場データの収集・保存・変換に関するコードを配置
- src/kabusys/strategy: 取引戦略の実装を配置
- src/kabusys/execution: ブローカー API 連携や注文管理を配置
- src/kabusys/monitoring: ログ出力・監視・メトリクス出力を配置

---

## 開発のヒント

- まずは各モジュールにインターフェース（抽象クラスや関数仕様）を定義すると、テストや置き換えが楽になります。
- ブローカー API（例: kabuステーション等）を使う場合は、APIキー/認証情報を環境変数や設定ファイルで安全に扱うこと。
- 実運用前にバックテスト環境やサンドボックスで十分に検証すること。
- ロギングと例外処理を充実させ、監視やアラートを用意してください。

---

必要であれば、README に以下を追加できます:
- 具体的な実装例（strategy、execution の完全サンプル）
- CI / テストの導入方法（pytest など）
- デプロイ / コンテナ化の手順（Dockerfile 等）

追加希望があれば、実装方針やサンプルコードの詳細を指定して下さい。