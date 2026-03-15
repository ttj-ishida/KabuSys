# KabuSys

日本株自動売買システム（KabuSys）は、データ取得、売買戦略、注文実行、監視を分離したモジュール構成で設計された軽量なテンプレートプロジェクトです。骨組みを提供し、各モジュールを実装することで自動売買ロジックを組み立てられるようになっています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つ4つのサブパッケージを含む Python パッケージです。

- data: 市場データの取得／整形を担当
- strategy: 売買アルゴリズムを実装
- execution: 証券会社API等への注文送信を担当
- monitoring: ログや稼働状況の監視・通知

現在はパッケージの骨組みのみを提供しており、各モジュールを実装して利用します。

---

## 機能一覧

- プロジェクト構成（srcレイアウト）と名前空間パッケージの準備
- サブパッケージ: `data`, `strategy`, `execution`, `monitoring`
- パッケージバージョン情報 (`kabusys.__version__`)

（注）実際のデータ取得や注文送信、戦略ロジックは本テンプレートには含まれていません。各モジュールに実装を追加してご利用ください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   - macOS / Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 開発インストール（editable）
   ```
   pip install -e .
   ```
   ※ `pyproject.toml` / `setup.cfg` が未作成の場合は、プロジェクトルートに適切なパッケージメタ情報を追加してください。
   最小限の `pyproject.toml` 例（PoetryやFlitを使う場合はそれぞれに合わせてください）：
   ```toml
   [build-system]
   requires = ["setuptools", "wheel"]
   build-backend = "setuptools.build_meta"
   ```

4. 依存パッケージがある場合は `requirements.txt` を用意してインストールしてください。
   ```
   pip install -r requirements.txt
   ```

---

## 使い方

現状はパッケージの枠組みのみ提供しています。以下は基本的なインポートと、各モジュールに実装を追加する際のサンプルスケルトンです。

- パッケージのバージョン確認
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

- 各モジュールのインポート（実装を追加後に利用）
```python
from kabusys import data, strategy, execution, monitoring
```

- サンプル: 各コンポーネントのインターフェース例（実装例）
```python
# src/kabusys/data/provider.py
class DataProvider:
    def get_latest_price(self, symbol: str) -> float:
        """指定銘柄の最新価格を取得する。実装必須。"""
        raise NotImplementedError

# src/kabusys/strategy/simple.py
class Strategy:
    def __init__(self, data_provider):
        self.data_provider = data_provider

    def should_buy(self, symbol: str) -> bool:
        """買い判定のロジックを実装"""
        raise NotImplementedError

    def should_sell(self, symbol: str) -> bool:
        """売り判定のロジックを実装"""
        raise NotImplementedError

# src/kabusys/execution/engine.py
class ExecutionEngine:
    def place_order(self, symbol: str, side: str, size: int):
        """注文を送信する。side は 'buy'/'sell' など"""
        raise NotImplementedError

# src/kabusys/monitoring/logger.py
class Monitor:
    def log(self, message: str):
        """ログ出力や通知を行う"""
        raise NotImplementedError
```

- 実行フロー例（非常に簡易）
```python
data_provider = MyDataProvider()         # data モジュール内で実装
strategy = MyStrategy(data_provider)     # strategy モジュールで実装
executor = MyExecutionEngine()           # execution モジュールで実装
monitor = MyMonitor()                    # monitoring モジュールで実装

symbol = "7203"  # 例: トヨタ自動車（銘柄コード）
price = data_provider.get_latest_price(symbol)
if strategy.should_buy(symbol):
    executor.place_order(symbol, side="buy", size=100)
    monitor.log(f"Bought {symbol} at {price}")
elif strategy.should_sell(symbol):
    executor.place_order(symbol, side="sell", size=100)
    monitor.log(f"Sold {symbol} at {price}")
```

---

## 開発・拡張ガイド

- data: Yahoo Finance、各証券会社API、CSV/DBなどのデータソースのラッパーを実装してください。キャッシュやレート制限、例外処理を考慮してください。
- strategy: 単純移動平均、RSI、機械学習ベースなどの戦略を実装します。バックテスト機能を別モジュールとして追加することを推奨します。
- execution: 実際の注文送信はリスクが高いため、まずは「ドライラン（サンドボックス）」を実装して安全検証を行ってください。再実行時の二重注文防止ロジックやエラーハンドリングを実装してください。
- monitoring: ログ、メトリクス、アラート（メール、Slack等）を統合すると運用しやすくなります。

テストやCIの導入も推奨します（pytest、GitHub Actionsなど）。

---

## ディレクトリ構成

現在の最小構成は次のとおりです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ定義（__version__ = "0.1.0"）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
```

拡張例（実装ファイルを追加した場合）:
```
src/kabusys/data/provider.py
src/kabusys/strategy/simple.py
src/kabusys/execution/engine.py
src/kabusys/monitoring/logger.py
tests/
README.md
pyproject.toml  # または setup.cfg/setup.py
requirements.txt
```

---

## 貢献・連絡

- バグ報告や機能提案は Issue を立ててください。
- プルリクエスト歓迎。コーディング規約やテストを添えてください。

---

以上がこのプロジェクトの README テンプレートです。必要であれば、具体的なインターフェース定義やサンプル実装（データプロバイダや注文実行ラッパー）を追加した README を作成します。どの部分を優先して詳細化したいか教えてください。