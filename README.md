# KabuSys

KabuSys は日本株の自動売買システムのための軽量な Python パッケージの雛形です。  
（現バージョン: 0.1.0）

このリポジトリは、データ取得、売買戦略、注文実行、監視の4 つの主要コンポーネントに分割された構造を提供します。実運用用のロジックは各モジュールを拡張して実装してください。

---

## 主な機能

- モジュール分割されたアーキテクチャ
  - data: 市場データの取得・整形を担当
  - strategy: 売買シグナルの生成を担当
  - execution: 注文の送信・管理を担当
  - monitoring: ログ、メトリクス、状態監視を担当
- パッケージ化された構造（src配下）
- 拡張・テストしやすい設計の雛形

---

## セットアップ手順

以下はローカル開発環境での基本的なセットアップ手順の例です。

1. Python 環境を準備（例: venv）

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージがあれば `requirements.txt`／`pyproject.toml` に従ってインストールします。現状は依存関係の定義がないため空でも問題ありません。

   ```bash
   pip install -U pip setuptools
   # 例: pip install -r requirements.txt
   ```

3. 開発中はパッケージを editable モードでインストールすると便利です（プロジェクトに pyproject.toml / setup.py がある前提）。

   ```bash
   pip install -e .
   ```

   もしパッケージ化していない場合は、プロジェクトのルートから Python のパスに `src` を追加して import できるようにしてください。

---

## 使い方（基本例）

パッケージをインストールすると、Python から次のように利用できます。

```python
import kabusys

print(kabusys.__version__)  # 0.1.0

# サブパッケージを参照
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

各モジュールは現状は空のパッケージですが、以下のようなインターフェースを実装することを想定しています。

- data
  - 例: fetch_price(symbol, start, end) -> pandas.DataFrame
- strategy
  - 例: class Strategy: def generate_signals(df) -> signals
- execution
  - 例: class Broker: def place_order(order) / def cancel_order(id)
- monitoring
  - 例: metrics, ログ出力, ヘルスチェック

簡単な利用例（擬似コード）：

```python
from kabusys.data import PriceFetcher
from kabusys.strategy import MyStrategy
from kabusys.execution import Broker
from kabusys.monitoring import Monitor

# 1) データ取得
prices = PriceFetcher().fetch_price("7203.T", "2023-01-01", "2023-03-01")

# 2) シグナル作成
signals = MyStrategy().generate_signals(prices)

# 3) 注文実行
broker = Broker()
for sig in signals:
    broker.place_order(sig)

# 4) モニタリング
Monitor().report()
```

（上記クラスは実装例です。用途に合わせて実装してください。）

---

## ディレクトリ構成

現在の主要ファイル構成は以下の通りです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ定義、バージョン情報
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
```

- src/kabusys/__init__.py にパッケージのメタ情報（__version__ 等）が定義されています。
- 各サブパッケージは現状空のテンプレートです。ここに機能を実装していきます。

---

## 開発・拡張のヒント

- 各サブパッケージは単一責任に従って実装してください（データ取得・戦略・実行・監視の分離）。
- テストを追加する際は、各モジュールごとにユニットテストを用意すると保守が楽になります（pytest を推奨）。
- 実運用で外部ブローカーへ接続する場合は、API キーやシークレットなどの機密情報を設定ファイルや環境変数で管理してください。
- ロギングと例外処理を適切に実装し、モニタリングツールやアラートと連携することを推奨します。

---

## ライセンス・貢献

本リポジトリは雛形です。実際に利用する際はライセンスの追加、README の整備、実装とテストの充実を行ってください。貢献や改良は Pull Request を歓迎します。

---

以上。必要があれば、具体的なクラス設計、サンプル実装、テストテンプレートなどの追加ドキュメントを作成します。どの部分を優先して欲しいか教えてください。