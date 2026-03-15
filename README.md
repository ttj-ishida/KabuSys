# KabuSys

KabuSys は日本株の自動売買システム開発を目的とした Python パッケージの骨組みです。モジュールはデータ取得（data）、戦略（strategy）、注文実行（execution）、監視（monitoring）に分割されており、これらを組み合わせて自動売買システムを構築できます。

バージョン: 0.1.0

---

## 機能一覧

- プロジェクト構成の提供（data / strategy / execution / monitoring の4つの主要パッケージ）
- 各機能ごとの分離により、モジュール単位での実装・テストが容易
- 開発用にすぐ取りかかれるシンプルなテンプレート

（注）現状はパッケージの骨組みのみを提供します。実際のデータ取得、注文発行、監視ロジックは利用者が実装する想定です。

---

## 前提条件

- Python 3.8 以上を推奨
- Git（ソース管理を行う場合）
- 実環境での注文やデータ取得を行うには、証券会社 API や認証情報などの準備が必要です（本リポジトリには含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）
   ```
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate      # macOS / Linux
   .venv\Scripts\activate         # Windows
   ```

3. インストール方法（プロジェクトがパッケージ化されている場合）
   - pyproject.toml / setup.py がある場合:
     ```
     python -m pip install -e .
     ```
   - 単純に src ディレクトリを参照する場合（開発時）:
     ```
     export PYTHONPATH=$(pwd)/src   # macOS / Linux
     set PYTHONPATH=%cd%\src        # Windows (PowerShell では $env:PYTHONPATH = "$pwd\src")
     ```

4. 依存パッケージがある場合は requirements.txt を使用してインストールしてください（本骨組みでは依存ファイルは含まれていません）。
   ```
   python -m pip install -r requirements.txt
   ```

---

## 使い方

このパッケージはモジュールの骨組みを提供します。まずはインポートしてバージョン確認や基本動作を確認できます。

例: パッケージ情報の確認
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

各サブパッケージは次のようにインポートできます（現状は空のパッケージです）。
```python
from kabusys import data, strategy, execution, monitoring
```

簡単な使用フロー（実装例のひな形）：
1. data パッケージに DataProvider を実装して価格や板情報を取得
2. strategy パッケージに Strategy を実装して売買判断を行う
3. execution パッケージに Executor を実装して注文を送信／キャンセル
4. monitoring パッケージに Monitor を実装してログ・通知・状態監視を行う

サンプルのクラス雛形（実装例）：
```python
# src/kabusys/strategy/simple_strategy.py
class SimpleStrategy:
    def __init__(self, data_provider, executor):
        self.data_provider = data_provider
        self.executor = executor

    def on_tick(self):
        price = self.data_provider.get_last_price("7203")  # 銘柄コード例
        # シンプルな売買ロジック
        if price is None:
            return
        if price < 2000:
            self.executor.buy("7203", 100)
        elif price > 2500:
            self.executor.sell("7203", 100)
```

注意: 実際の注文処理や API 呼び出しは例外処理、レート制限対応、認証情報の管理（環境変数や秘密管理）を必ず実装してください。

---

## ディレクトリ構成

リポジトリ（抜粋）の構成は以下のようになっています。

```
src/
└── kabusys/
    ├── __init__.py           # パッケージ情報（__version__ 等）
    ├── data/
    │   └── __init__.py       # データ取得（価格、板、約定履歴 など）
    ├── strategy/
    │   └── __init__.py       # 売買戦略（シグナル生成）
    ├── execution/
    │   └── __init__.py       # 注文実行（発注・取消）
    └── monitoring/
        └── __init__.py       # ログ・監視・通知
```

ファイル例（現在の中身）:
- src/kabusys/__init__.py
  - パッケージ docstring と __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]
- src/kabusys/data/__init__.py（空）
- src/kabusys/strategy/__init__.py（空）
- src/kabusys/execution/__init__.py（空）
- src/kabusys/monitoring/__init__.py（空）

---

## 拡張ガイド（短め）

- data:
  - REST/WebSocket 経由でティックや板情報を取得するクラスを実装
  - 取得したデータはスレッドセーフにキャッシュ／公開することを推奨

- strategy:
  - 単一のインターフェース（例: on_tick / on_bar）を決め、複数戦略で共通化
  - パラメータ化してバックテストと本番実行で共通のコードを使えるようにする

- execution:
  - 注文ID管理、約定確認、再試行ロジックを実装
  - サンドボックス環境やペーパートレード対応を用意すると安全

- monitoring:
  - ログ（INFO/ERROR）出力、アラート（メール/Slack 等）を実装
  - 監視ダッシュボードやメトリクス収集を追加することで運用性が向上

---

必要に応じて README を更新してください。実装に関する質問や具体的な設計相談があれば、詳細（使いたい証券会社 API、想定戦略、リアルタイム要件 など）を教えてください。